# Open URL opens selected URLs, files, folders, or googles text
# Hosted at http://github.com/noahcoad/open-url
# test urls: google.com ~/tmp ~/tmp/tmp c:\noah c:\noah\tmp.txt c:\noah\tmp

import sublime
import sublime_plugin

import os
import platform
import re
import fnmatch
import socket
import subprocess
import threading
import urllib
import urllib.parse
import webbrowser

debug = True

SPEC = {
    # dir explorer
    'dir': {
        'Darwin':       ['open', '<__path__>'],
        'Linux':        ['nautilus', '--browser', '<__path__>'],
        'Windows':      ['explorer', '<__path__>']
    },
    # file explorer
    'file': {
        'Darwin':       ['open', '-R', '<__path__>'],
        'Linux':        ['nautilus', '--browser', '<__path__>'],
        'Windows':      ['explorer /select,"<__path__>"']
    },
    'detech_run': {
        'Darwin':       ['nohup', '*__path__*'], 
        'Linux':        ['nohup', '*__path__*'], 
        'Windows':      ['start', '', '/I', '*__path__*']
    },
    # desktop open
    'open': {
        'Darwin':       ['open', '<__path__>'],
        'Linux':        ['xdg-open', '<__path__>'],
        'Windows':      ['<__path__>'],
    },
    'open_with_app': {
        'Darwin':       ['open', '-a', '<__app__>', '<__path__>']
    },
    'run_custom': {
        'Darwin':       ['*__app__*', '*__path__*'],
        'Linux':        ['*__app__*', '*__path__*'],
        'Windows':      ['*__app__*', '*__path__*']
    },
    'shell': {
        'Darwin':       ['/bin/sh', '-c', '*__path__*'],
        'Linux':        ['/bin/sh', '-c', '*__path__*'],
        'Windows':      ['cmd.exe /c "<__path__>"']         # need extra hidden at Popen
    },
    'shell_keep_open': {
        'Darwin':       ['/bin/sh', '-c', "'<__path__>; exec /bin/sh'"],
        'Linux':        ['/bin/sh', '-c', "'<__path__>; exec /bin/sh'"],
        'Windows':      ['cmd.exe /k "<__path__>"']
    },
    # terminal open
    # terminal_keep_open = terminal + shell_keep_open
    'terminal': {
        'Darwin':       ['/opt/X11/bin/xterm', '-e', '*__path__*'],
        'Linux':        ['/usr/bin/xterm', '-e', '*__path__*'],
        'Linux2':       ['gnome-terminal', '-x', '*__path__*'],
        'Windows':      ['cmd.exe /c "<__path__>"']
    },

    # termain open with pause after running
    # 'pause': {
    #     'Darwin':       ['<__path__>; read -p "Press [ENTER] to continue..."'],
    #     'Linux':        ['<__path__>; read -p "Press [ENTER] to continue..."'],
    #     'Windows':      ['<__path__> & pause']
    # }
}

class Specification:
    dry_run = False
    def __init__(self, args, hidden=False):
        self.args = args
        self.hidden = hidden

    def quote(self):
        self.args = ['"{}"'.format(arg) for arg in self.args]

    def popen(self, cwd=None):
        if debug:
            print("popen cmd: %s" % self.args)
        if self.dry_run:
            return

        startupinfo = None
        if self.hidden:
            from subprocess import STARTUPINFO, _winapi
            startupinfo = STARTUPINFO()
            startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = _winapi.SW_HIDE

        subprocess.Popen(self.args[0] if len(self.args) == 1 else self.args, cwd=cwd, startupinfo=startupinfo)

    @classmethod
    def get_spec(cls, intention, path, app=None, terminal=None):
        if not SPEC.get(intention):
            raise Exception('unrecognized intention "{}"'.format(intention))
        if not SPEC[intention].get(platform.system()):
            raise Exception('unsupported os')
        spec = SPEC[intention][platform.system()]
        
        def merge(target, token, source):
            if source is None:
                return target
            if isinstance(source, cls):
                source = source.args
            if not isinstance(source, list):
                source = [source]
            source_str = ' '.join(s if s else '""' for s in source)
            merged = []
            for arg in target:
                if arg == '*__{}__*'.format(token):
                    merged.extend(source)
                else:
                    merged.append(arg.replace('<__{}__>'.format(token), source_str))
            return merged

        spec = merge(spec, 'path', path)
        spec = merge(spec, 'app', app)
        hidden = intention == 'shell' and platform.system() == 'Windows'
        return cls(spec, hidden=hidden)



class ActionDispitch:
    default_autoinfo = [
        {'type':'file', 'action': 'menu'},
        {'type':'folder', 'action': 'folder_menu'},
        {'type':'web', 'pattern':['*://*'], 'action': 'browse'},
        {'type':'web', 'regex':r"\w[^\s]*\.(?:%s)[^\s]*\Z" % OpenUrlMoreCommand.domains, 'action': 'browse_http'},
        {'action': 'browse_google'},
    ]

    def __init__(self, view, path_type, path, autoinfo=None):
        self.path = path
        self.type = path_type
        self.view = view
        self.autoinfo = autoinfo or self.get_autoinfo()

    def get_spec(self, *args, **kwargs):
        return Specification.get_spec(*args, **kwargs)

    def get_autoinfo(self):
        config = sublime.load_settings("open_url.sublime-settings")

        selected = []
        # see if there's already an action defined for this file
        for auto in config.get('autoactions', []) + self.default_autoinfo:
            # see if this line applies to this opperating system
            oscheck = ('os' not in auto
                       or auto['os'] == 'win' and platform.system() == 'Windows'
                       or auto['os'] == 'linux' and platform.system() == 'Linux'
                       or auto['os'] == 'mac' and platform.system() == 'Darwin'
                       or auto['os'] == 'posix' and (platform.system() == 'Darwin' or platform.system() == 'Linux')  
                       )

            # if the line is for this OS, then check to see if we have a file pattern match
            
            for pattern in auto.get('pattern', ['*']):
                match = all([oscheck,
                             fnmatch.fnmatch(self.path, pattern),
                             not (auto.get('type') and auto['type'] != self.type),
                             not (auto.get('regex') and not re.search(auto['regex'], self.path, re.IGNORECASE))
                             ])
                if match:
                    selected.append((
                                    -({'any':0, 'posix':1}).get(auto.get('os', 'any'), 2),
                                    -sum(2 if c == '*' else 1 for c in pattern) - int('regex' in auto) * 10,
                                    -int('type' in auto),
                                    auto
                                    ))
                    break
        if debug: print(selected)
        # give higher priority to the exact option
        assert(selected)
        selected = sorted(selected)
        return selected[0][3]
        

    def do_action(self, action=None, **kwargs):
        action = action or self.autoinfo['action']
        if debug: print('path: {}'.format(self.path))
        if debug: print('action: {}, autoinfo:{}'.format(action, self.autoinfo))
        if not hasattr(self, 'action_{}'.format(action)):
            raise Exception("undefined action")
        method = getattr(self, 'action_{}'.format(action))
        method()

    def action_reveal(self):
        """ Show the system file manager that select this file """
        spec = self.get_spec('dir' if os.path.isdir(self.path) else 'file', self.path)
        spec.popen()

    def action_open(self):
        autoinfo = self.autoinfo
        if autoinfo.get('app'):
            # OSX only
            spec = self.get_spec('open_with_app', self.path, app=autoinfo['app'])
        else:
            # default methods to open files
            spec = self.get_spec('open', self.path)
        spec.popen()

    def action_terminal(self, spec=None):
        """ run command in a terminal and pause if desired """
        autoinfo = self.autoinfo
        spec = spec or self.path
        if autoinfo.get('pause'):
            spec = self.get_spec('pause', spec)
        if autoinfo.get('keep_open'):
            spec = self.get_spec('shell_keep_open', spec)
        spec = self.get_spec('terminal', spec)
        spec.popen()
            

    def action_run(self):
        if autoinfo.get('openwith'):
            # check if there are special instructions to open this file
            spec = self.get_spec('run_custom', self.path, app=autoinfo['openwith'])
        if autoinfo.get('terminal'):
            return self.action_terminal(self, spec)

        # run in detach process through regular way
        spec = self.get_spec('detech_run', self.path)
        spec.popen(cwd=os.path.dirname(self.path))

    def action_edit(self):
        # open the file for editing in sublime
        self.view.window().open_file(self.path)

    def action_edit_in_new_window(self):
        args = []
        executable_path = sublime.executable_path()
        if sublime.platform() == 'osx':
            app_path = executable_path[:executable_path.rfind(".app/")+5]
            executable_path = app_path+"Contents/SharedSupport/bin/subl"
        else:
            executable_path = os.path.join(os.path.dirname(executable_path), 'subl')

        args.append(executable_path)
        path = os.path.abspath(self.path)
        
        args.append(path)
        spec = Specification(args)
        spec.quote()
        spec = self.get_spec('detech_run', spec)
        spec = self.get_spec('shell', spec)
        spec.popen()
        #subprocess.Popen(items, cwd=items[1])

    def action_browse(self):
        webbrowser.open_new_tab(self.path)

    def action_browse_http(self):
        if not "://" in self.path:
            self.path = "http://" + self.path
        self.do_action('browse')

    def action_browse_google(self):
        self.path = "http://google.com/#q=" + urllib.parse.quote(self.path, '')
        self.do_action('browse')

    def action_add_folder_to_project(self):
        d = self.view.window().project_data() or {}
        d.setdefault('folders', []).append({'path': self.path})
        self.view.window().set_project_data(d)


    # for files, as the user if they's like to edit or run the file
    def action_menu(self):
        self.show_action_panel(['edit',
                                'run',
                                'reveal',
                                'edit in new window',
                                'open'
                                ])


    def action_folder_menu(self):
        self.show_action_panel(['reveal',
                                'add folder to project',
                                'edit in new window'
                                ])

    def show_action_panel(self, menu):
        def do(idx):
            if idx != -1:
                self.do_action(menu[idx].replace(' ', '_'))
        sublime.active_window().show_quick_panel(menu, do)



class OpenUrlMoreCommand(sublime_plugin.TextCommand):

    # enter debug mode on Noah's machine
    if debug: print("open_url running in verbose debug mode")

    # list of known domains for short urls, like ironcowboy.co
    domains = "AAA|AARP|ABB|ABBOTT|ABBVIE|ABOGADO|ABUDHABI|AC|ACADEMY|ACCENTURE|ACCOUNTANT|ACCOUNTANTS|ACO|ACTIVE|ACTOR|AD|ADAC|ADS|ADULT|AE|AEG|AERO|AF|AFL|AG|AGAKHAN|AGENCY|AI|AIG|AIRFORCE|AIRTEL|AKDN|AL|ALIBABA|ALIPAY|ALLFINANZ|ALLY|ALSACE|AM|AMICA|AMSTERDAM|ANALYTICS|ANDROID|ANQUAN|AO|APARTMENTS|APP|APPLE|AQ|AQUARELLE|AR|ARAMCO|ARCHI|ARMY|ARPA|ARTE|AS|ASIA|ASSOCIATES|AT|ATTORNEY|AU|AUCTION|AUDI|AUDIO|AUTHOR|AUTO|AUTOS|AVIANCA|AW|AWS|AX|AXA|AZ|AZURE|BA|BABY|BAIDU|BAND|BANK|BAR|BARCELONA|BARCLAYCARD|BARCLAYS|BAREFOOT|BARGAINS|BAUHAUS|BAYERN|BB|BBC|BBVA|BCG|BCN|BD|BE|BEATS|BEER|BENTLEY|BERLIN|BEST|BET|BF|BG|BH|BHARTI|BI|BIBLE|BID|BIKE|BING|BINGO|BIO|BIZ|BJ|BLACK|BLACKFRIDAY|BLOOMBERG|BLUE|BM|BMS|BMW|BN|BNL|BNPPARIBAS|BO|BOATS|BOEHRINGER|BOM|BOND|BOO|BOOK|BOOTS|BOSCH|BOSTIK|BOT|BOUTIQUE|BR|BRADESCO|BRIDGESTONE|BROADWAY|BROKER|BROTHER|BRUSSELS|BS|BT|BUDAPEST|BUGATTI|BUILD|BUILDERS|BUSINESS|BUY|BUZZ|BV|BW|BY|BZ|BZH|CA|CAB|CAFE|CAL|CALL|CAMERA|CAMP|CANCERRESEARCH|CANON|CAPETOWN|CAPITAL|CAR|CARAVAN|CARDS|CARE|CAREER|CAREERS|CARS|CARTIER|CASA|CASH|CASINO|CAT|CATERING|CBA|CBN|CC|CD|CEB|CENTER|CEO|CERN|CF|CFA|CFD|CG|CH|CHANEL|CHANNEL|CHASE|CHAT|CHEAP|CHLOE|CHRISTMAS|CHROME|CHURCH|CI|CIPRIANI|CIRCLE|CISCO|CITIC|CITY|CITYEATS|CK|CL|CLAIMS|CLEANING|CLICK|CLINIC|CLINIQUE|CLOTHING|CLOUD|CLUB|CLUBMED|CM|CN|CO|COACH|CODES|COFFEE|COLLEGE|COLOGNE|COM|COMMBANK|COMMUNITY|COMPANY|COMPARE|COMPUTER|COMSEC|CONDOS|CONSTRUCTION|CONSULTING|CONTACT|CONTRACTORS|COOKING|COOL|COOP|CORSICA|COUNTRY|COUPON|COUPONS|COURSES|CR|CREDIT|CREDITCARD|CREDITUNION|CRICKET|CROWN|CRS|CRUISES|CSC|CU|CUISINELLA|CV|CW|CX|CY|CYMRU|CYOU|CZ|DABUR|DAD|DANCE|DATE|DATING|DATSUN|DAY|DCLK|DDS|DE|DEALER|DEALS|DEGREE|DELIVERY|DELL|DELOITTE|DELTA|DEMOCRAT|DENTAL|DENTIST|DESI|DESIGN|DEV|DIAMONDS|DIET|DIGITAL|DIRECT|DIRECTORY|DISCOUNT|DJ|DK|DM|DNP|DO|DOCS|DOG|DOHA|DOMAINS|DOWNLOAD|DRIVE|DUBAI|DURBAN|DVAG|DZ|EARTH|EAT|EC|EDEKA|EDU|EDUCATION|EE|EG|EMAIL|EMERCK|ENERGY|ENGINEER|ENGINEERING|ENTERPRISES|EPSON|EQUIPMENT|ER|ERNI|ES|ESQ|ESTATE|ET|EU|EUROVISION|EUS|EVENTS|EVERBANK|EXCHANGE|EXPERT|EXPOSED|EXPRESS|EXTRASPACE|FAGE|FAIL|FAIRWINDS|FAITH|FAMILY|FAN|FANS|FARM|FASHION|FAST|FEEDBACK|FERRERO|FI|FILM|FINAL|FINANCE|FINANCIAL|FIRESTONE|FIRMDALE|FISH|FISHING|FIT|FITNESS|FJ|FK|FLICKR|FLIGHTS|FLIR|FLORIST|FLOWERS|FLSMIDTH|FLY|FM|FO|FOO|FOOTBALL|FORD|FOREX|FORSALE|FORUM|FOUNDATION|FOX|FR|FRESENIUS|FRL|FROGANS|FRONTIER|FTR|FUND|FURNITURE|FUTBOL|FYI|GA|GAL|GALLERY|GALLO|GALLUP|GAME|GARDEN|GB|GBIZ|GD|GDN|GE|GEA|GENT|GENTING|GF|GG|GGEE|GH|GI|GIFT|GIFTS|GIVES|GIVING|GL|GLASS|GLE|GLOBAL|GLOBO|GM|GMAIL|GMBH|GMO|GMX|GN|GOLD|GOLDPOINT|GOLF|GOO|GOOG|GOOGLE|GOP|GOT|GOV|GP|GQ|GR|GRAINGER|GRAPHICS|GRATIS|GREEN|GRIPE|GROUP|GS|GT|GU|GUARDIAN|GUCCI|GUGE|GUIDE|GUITARS|GURU|GW|GY|HAMBURG|HANGOUT|HAUS|HDFCBANK|HEALTH|HEALTHCARE|HELP|HELSINKI|HERE|HERMES|HIPHOP|HITACHI|HIV|HK|HKT|HM|HN|HOCKEY|HOLDINGS|HOLIDAY|HOMEDEPOT|HOMES|HONDA|HORSE|HOST|HOSTING|HOTELES|HOTMAIL|HOUSE|HOW|HR|HSBC|HT|HTC|HU|HYUNDAI|IBM|ICBC|ICE|ICU|ID|IE|IFM|IINET|IL|IM|IMAMAT|IMMO|IMMOBILIEN|IN|INDUSTRIES|INFINITI|INFO|ING|INK|INSTITUTE|INSURANCE|INSURE|INT|INTERNATIONAL|INVESTMENTS|IO|IPIRANGA|IQ|IR|IRISH|IS|ISELECT|ISMAILI|IST|ISTANBUL|IT|ITAU|IWC|JAGUAR|JAVA|JCB|JCP|JE|JETZT|JEWELRY|JLC|JLL|JM|JMP|JNJ|JO|JOBS|JOBURG|JOT|JOY|JP|JPMORGAN|JPRS|JUEGOS|KAUFEN|KDDI|KE|KERRYHOTELS|KERRYLOGISTICS|KERRYPROPERTIES|KFH|KG|KH|KI|KIA|KIM|KINDER|KITCHEN|KIWI|KM|KN|KOELN|KOMATSU|KP|KPMG|KPN|KR|KRD|KRED|KUOKGROUP|KW|KY|KYOTO|KZ|LA|LACAIXA|LAMBORGHINI|LAMER|LANCASTER|LAND|LANDROVER|LANXESS|LASALLE|LAT|LATROBE|LAW|LAWYER|LB|LC|LDS|LEASE|LECLERC|LEGAL|LEXUS|LGBT|LI|LIAISON|LIDL|LIFE|LIFEINSURANCE|LIFESTYLE|LIGHTING|LIKE|LIMITED|LIMO|LINCOLN|LINDE|LINK|LIPSY|LIVE|LIVING|LIXIL|LK|LOAN|LOANS|LOCUS|LOL|LONDON|LOTTE|LOTTO|LOVE|LR|LS|LT|LTD|LTDA|LU|LUPIN|LUXE|LUXURY|LV|LY|MA|MADRID|MAIF|MAISON|MAKEUP|MAN|MANAGEMENT|MANGO|MARKET|MARKETING|MARKETS|MARRIOTT|MBA|MC|MD|ME|MED|MEDIA|MEET|MELBOURNE|MEME|MEMORIAL|MEN|MENU|MEO|METLIFE|MG|MH|MIAMI|MICROSOFT|MIL|MINI|MK|ML|MLS|MM|MMA|MN|MO|MOBI|MOBILY|MODA|MOE|MOI|MOM|MONASH|MONEY|MONTBLANC|MORMON|MORTGAGE|MOSCOW|MOTORCYCLES|MOV|MOVIE|MOVISTAR|MP|MQ|MR|MS|MT|MTN|MTPC|MTR|MU|MUSEUM|MUTUAL|MUTUELLE|MV|MW|MX|MY|MZ|NA|NADEX|NAGOYA|NAME|NATURA|NAVY|NC|NE|NEC|NET|NETBANK|NETWORK|NEUSTAR|NEW|NEWS|NEXT|NEXTDIRECT|NEXUS|NF|NG|NGO|NHK|NI|NICO|NIKON|NINJA|NISSAN|NISSAY|NL|NO|NOKIA|NORTHWESTERNMUTUAL|NORTON|NOWRUZ|NOWTV|NP|NR|NRA|NRW|NTT|NU|NYC|NZ|OBI|OFFICE|OKINAWA|OLAYAN|OLAYANGROUP|OM|OMEGA|ONE|ONG|ONL|ONLINE|OOO|ORACLE|ORANGE|ORG|ORGANIC|ORIGINS|OSAKA|OTSUKA|OVH|PA|PAGE|PAMPEREDCHEF|PANERAI|PARIS|PARS|PARTNERS|PARTS|PARTY|PASSAGENS|PCCW|PE|PET|PF|PG|PH|PHARMACY|PHILIPS|PHOTO|PHOTOGRAPHY|PHOTOS|PHYSIO|PIAGET|PICS|PICTET|PICTURES|PID|PIN|PING|PINK|PIZZA|PK|PL|PLACE|PLAY|PLAYSTATION|PLUMBING|PLUS|PM|PN|POHL|POKER|PORN|POST|PR|PRAXI|PRESS|PRO|PROD|PRODUCTIONS|PROF|PROGRESSIVE|PROMO|PROPERTIES|PROPERTY|PROTECTION|PS|PT|PUB|PW|PWC|PY|QA|QPON|QUEBEC|QUEST|RACING|RE|READ|REALTOR|REALTY|RECIPES|RED|REDSTONE|REDUMBRELLA|REHAB|REISE|REISEN|REIT|REN|RENT|RENTALS|REPAIR|REPORT|REPUBLICAN|REST|RESTAURANT|REVIEW|REVIEWS|REXROTH|RICH|RICHARDLI|RICOH|RIO|RIP|RO|ROCHER|ROCKS|RODEO|ROOM|RS|RSVP|RU|RUHR|RUN|RW|RWE|RYUKYU|SA|SAARLAND|SAFE|SAFETY|SAKURA|SALE|SALON|SAMSUNG|SANDVIK|SANDVIKCOROMANT|SANOFI|SAP|SAPO|SARL|SAS|SAXO|SB|SBI|SBS|SC|SCA|SCB|SCHAEFFLER|SCHMIDT|SCHOLARSHIPS|SCHOOL|SCHULE|SCHWARZ|SCIENCE|SCOR|SCOT|SD|SE|SEAT|SECURITY|SEEK|SELECT|SENER|SERVICES|SEVEN|SEW|SEX|SEXY|SFR|SG|SH|SHARP|SHAW|SHELL|SHIA|SHIKSHA|SHOES|SHOUJI|SHOW|SHRIRAM|SI|SINA|SINGLES|SITE|SJ|SK|SKI|SKIN|SKY|SKYPE|SL|SM|SMILE|SN|SNCF|SO|SOCCER|SOCIAL|SOFTBANK|SOFTWARE|SOHU|SOLAR|SOLUTIONS|SONG|SONY|SOY|SPACE|SPIEGEL|SPOT|SPREADBETTING|SR|SRL|ST|STADA|STAR|STARHUB|STATEBANK|STATEFARM|STATOIL|STC|STCGROUP|STOCKHOLM|STORAGE|STORE|STREAM|STUDIO|STUDY|STYLE|SU|SUCKS|SUPPLIES|SUPPLY|SUPPORT|SURF|SURGERY|SUZUKI|SV|SWATCH|SWISS|SX|SY|SYDNEY|SYMANTEC|SYSTEMS|SZ|TAB|TAIPEI|TALK|TAOBAO|TATAMOTORS|TATAR|TATTOO|TAX|TAXI|TC|TCI|TD|TEAM|TECH|TECHNOLOGY|TEL|TELECITY|TELEFONICA|TEMASEK|TENNIS|TEVA|TF|TG|TH|THD|THEATER|THEATRE|TICKETS|TIENDA|TIFFANY|TIPS|TIRES|TIROL|TJ|TK|TL|TM|TMALL|TN|TO|TODAY|TOKYO|TOOLS|TOP|TORAY|TOSHIBA|TOTAL|TOURS|TOWN|TOYOTA|TOYS|TR|TRADE|TRADING|TRAINING|TRAVEL|TRAVELERS|TRAVELERSINSURANCE|TRUST|TRV|TT|TUBE|TUI|TUNES|TUSHU|TV|TVS|TW|TZ|UA|UBS|UG|UK|UNICOM|UNIVERSITY|UNO|UOL|US|UY|UZ|VA|VACATIONS|VANA|VC|VE|VEGAS|VENTURES|VERISIGN|VERSICHERUNG|VET|VG|VI|VIAJES|VIDEO|VIG|VIKING|VILLAS|VIN|VIP|VIRGIN|VISION|VISTA|VISTAPRINT|VIVA|VLAANDEREN|VN|VODKA|VOLKSWAGEN|VOTE|VOTING|VOTO|VOYAGE|VU|VUELOS|WALES|WALTER|WANG|WANGGOU|WARMAN|WATCH|WATCHES|WEATHER|WEATHERCHANNEL|WEBCAM|WEBER|WEBSITE|WED|WEDDING|WEIBO|WEIR|WF|WHOSWHO|WIEN|WIKI|WILLIAMHILL|WIN|WINDOWS|WINE|WME|WOLTERSKLUWER|WORK|WORKS|WORLD|WS|WTC|WTF|XBOX|XEROX|XIHUAN|XIN|XN--11B4C3D|XN--1CK2E1B|XN--1QQW23A|XN--30RR7Y|XN--3BST00M|XN--3DS443G|XN--3E0B707E|XN--3PXU8K|XN--42C2D9A|XN--45BRJ9C|XN--45Q11C|XN--4GBRIM|XN--55QW42G|XN--55QX5D|XN--5TZM5G|XN--6FRZ82G|XN--6QQ986B3XL|XN--80ADXHKS|XN--80AO21A|XN--80ASEHDB|XN--80ASWG|XN--8Y0A063A|XN--90A3AC|XN--90AIS|XN--9DBQ2A|XN--9ET52U|XN--9KRT00A|XN--B4W605FERD|XN--BCK1B9A5DRE4C|XN--C1AVG|XN--C2BR7G|XN--CCK2B3B|XN--CG4BKI|XN--CLCHC0EA0B2G2A9GCD|XN--CZR694B|XN--CZRS0T|XN--CZRU2D|XN--D1ACJ3B|XN--D1ALF|XN--E1A4C|XN--ECKVDTC9D|XN--EFVY88H|XN--ESTV75G|XN--FCT429K|XN--FHBEI|XN--FIQ228C5HS|XN--FIQ64B|XN--FIQS8S|XN--FIQZ9S|XN--FJQ720A|XN--FLW351E|XN--FPCRJ9C3D|XN--FZC2C9E2C|XN--FZYS8D69UVGM|XN--G2XX48C|XN--GCKR3F0F|XN--GECRJ9C|XN--H2BRJ9C|XN--HXT814E|XN--I1B6B1A6A2E|XN--IMR513N|XN--IO0A7I|XN--J1AEF|XN--J1AMH|XN--J6W193G|XN--JLQ61U9W7B|XN--JVR189M|XN--KCRX77D1X4A|XN--KPRW13D|XN--KPRY57D|XN--KPU716F|XN--KPUT3I|XN--L1ACC|XN--LGBBAT1AD8J|XN--MGB9AWBF|XN--MGBA3A3EJT|XN--MGBA3A4F16A|XN--MGBA7C0BBN0A|XN--MGBAAM7A8H|XN--MGBAB2BD|XN--MGBAYH7GPA|XN--MGBB9FBPOB|XN--MGBBH1A71E|XN--MGBC0A9AZCG|XN--MGBCA7DZDO|XN--MGBERP4A5D4AR|XN--MGBPL2FH|XN--MGBT3DHD|XN--MGBTX2B|XN--MGBX4CD0AB|XN--MIX891F|XN--MK1BU44C|XN--MXTQ1M|XN--NGBC5AZD|XN--NGBE9E0A|XN--NODE|XN--NQV7F|XN--NQV7FS00EMA|XN--NYQY26A|XN--O3CW4H|XN--OGBPF8FL|XN--P1ACF|XN--P1AI|XN--PBT977C|XN--PGBS0DH|XN--PSSY2U|XN--Q9JYB4C|XN--QCKA1PMC|XN--QXAM|XN--RHQV96G|XN--ROVU88B|XN--S9BRJ9C|XN--SES554G|XN--T60B56A|XN--TCKWE|XN--UNUP4Y|XN--VERMGENSBERATER-CTB|XN--VERMGENSBERATUNG-PWB|XN--VHQUV|XN--VUQ861B|XN--W4R85EL8FHU5DNRA|XN--W4RS40L|XN--WGBH1C|XN--WGBL6A|XN--XHQ521B|XN--XKC2AL3HYE2A|XN--XKC2DL3A5EE0H|XN--Y9A3AQ|XN--YFRO4I67O|XN--YGBI2AMMX|XN--ZFR164B|XPERIA|XXX|XYZ|YACHTS|YAHOO|YAMAXUN|YANDEX|YE|YODOBASHI|YOGA|YOKOHAMA|YOU|YOUTUBE|YT|YUN|ZA|ZARA|ZERO|ZIP|ZM|ZONE|ZUERICH|ZW"
    # domains = "|".join([x for x in open('tlds-alpha-by-domain.txt').read().split('\n') if x[0:1] != "#"])

    def run(self, edit=None, url=None):

        # sublime text has its own open_url command used for things like Help menu > Documentation
        # so if a url is specified, then open it instead of getting text from the edit window
        if url is None:
            url = self.selection()
        if not url:
            return

        # expand variables in the path
        url = os.path.expandvars(url)

        # strip quotes if quoted
        if (url.startswith("\"") & url.endswith("\"")) | (url.startswith("\'") & url.endswith("\'")):
            url = url[1:-1]

        # find the relative path to the current file 'google.com'
        try:
            relative_path = os.path.normpath(os.path.join(os.path.dirname(self.view.file_name()), url))
        except (TypeError, AttributeError):
            relative_path = None

        # debug info
        if debug: print("open_url debug : ", [url, relative_path])

        # if this is a directory, show it (absolute or relative)
        # if it is a path to a file, open the file in sublime (absolute or relative)
        # if it is a URL, open in browser
        # otherwise google it
        if os.path.isdir(url):
            ActionDispitch(self.view, 'folder', url).do_action()
        
        elif os.path.isdir(os.path.expanduser(url)):
            ActionDispitch(self.view, 'folder', os.path.expanduser(url)).do_action()

        elif relative_path and os.path.isdir(relative_path):
            ActionDispitch(self.view, 'folder', relative_path).do_action()
        
        elif os.path.exists(url):
            ActionDispitch(self.view, 'file', url).do_action()

        elif os.path.exists(os.path.expanduser(url)):
            ActionDispitch(self.view, 'file', os.path.expanduser(url)).do_action()
        
        elif relative_path and os.path.exists(relative_path):
            ActionDispitch(self.view, 'file', relative_path).do_action()
        
        else:
            ActionDispitch(self.view, 'web', url).do_action()


    # pulls the current selection or url under the cursor
    def selection(self):
        # new method to strongly enhance finding path-like string        
        s = self.view.sel()[0]

        # expand selection to possible URL
        start = s.a
        end = s.b

        # match absolute path ex: c:/xxx, E:\xxx, /xxx
        # this match is accept only one space inside word
        abs_url = r'([A-Z]:)?[\\/](?:[^ ]| (?! |https?:))*'
        
        # match url path ex: http://xxx, xxx/xxx, xxx\xxx
        # this match not accept space
        file_url = r'(https?://)?([^ \\/]+[\\/])+([^ \\/]+)?'
        
        # unfold surrounding symbol
        merge_url = r'(\[)?(\()?(?P<url>{0})(?(2)\))(?(1)\])'

        # compose those matches together
        url_pattern = re.compile(merge_url.format('|'.join([abs_url, file_url])), re.I)


        # if nothing is selected, expand selection to nearest terminators
        if (start == end):
            line_region = self.view.line(start)
            terminator = list('\t\"\'><,;')

            # move the selection back to the start of the url
            while (start > line_region.a
                   and not self.view.substr(start - 1) in terminator):
                start -= 1

            # move end of selection forward to the end of the url
            while (end < line_region.b
                   and not self.view.substr(end) in terminator):
                end += 1

            url = self.view.substr(sublime.Region(start, end))
            for match in url_pattern.finditer(url):
                # make sure match at the cursor position
                if match.span('url')[0] < s.a - line_region.a < match.span('url')[1]:
                    return match.group('url') 

        # grab the URL
        return self.view.substr(sublime.Region(start, end)).strip()



