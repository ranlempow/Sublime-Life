
# This is the basic material from which compiled templates will be formed.
# It will be manipulated in its string form at the `coffeekup.compile` function
# to generate the final template function. 
skeleton = (data = {}) ->
  # Whether to generate formatted HTML with indentation and line breaks, or
  # just the natural "faux-minified" output.
  data.format ?= off

  # Whether to autoescape all content or let you handle it on a case by case
  # basis with the `h` function.
  data.autoescape ?= off

  # Internal CoffeeKup stuff.
  __ck =
    
    # Adapter to keep the builtin tag functions DRY.
    tag: (name, args) ->
      combo = [name]
      combo.push i for i in args
      tag.apply data, combo

    render_idclass: (str) ->
      classes = []
        
      for i in str.split '.'
        if '#' in i
          id = i.replace '#', ''
        else
          classes.push i unless i is ''
            
      text " id=\"#{id}\"" if id
      
      if classes.length > 0
        text " class=\""
        for c in classes
          text ' ' unless c is classes[0]
          text c
        text '"'

    render_attrs: (obj, prefix = '') ->
      for k, v of obj
        # `true` is rendered as `selected="selected"`.
        v = k if typeof v is 'boolean' and v
        
        # Functions are rendered in an executable form.
        v = "(#{v}).call(this);" if typeof v is 'function'

        # Prefixed attribute.
        if typeof v is 'object' and v not instanceof Array
          # `data: {icon: 'foo'}` is rendered as `data-icon="foo"`.
          @render_attrs(v, prefix + k + '-')
        # `undefined`, `false` and `null` result in the attribute not being rendered.
        else if v
          # strings, numbers, arrays and functions are rendered "as is".
          text " #{prefix + k}=\"#{@esc(v)}\""


unless window?
  coffeekup.adapters =
    # Legacy adapters for when CoffeeKup expected data in the `context` attribute.
    simple: coffeekup.render
    meryl: coffeekup.render
    
    express:
      TemplateError: class extends Error
        constructor: (@message) ->
          Error.call this, @message
          Error.captureStackTrace this, arguments.callee
        name: 'TemplateError'
        
      compile: (template, data) -> 
        # Allows `partial 'foo'` instead of `text @partial 'foo'`.
        data.hardcode ?= {}
        data.hardcode.partial = ->
          text @partial.apply @, arguments
        
        TemplateError = @TemplateError
        try tpl = coffeekup.compile(template, data)
        catch e then throw new TemplateError "Error compiling #{data.filename}: #{e.message}"
        
        return ->
          try tpl arguments...
          catch e then throw new TemplateError "Error rendering #{data.filename}: #{e.message}"