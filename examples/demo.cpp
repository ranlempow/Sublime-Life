class dynamic_vertex_properties_writer
{
public:
  dynamic_vertex_properties_writer(const dynamic_properties& dp,
                                   const std::string& node_id)
    : dp(&dp), node_id(&node_id) { }

  template<typename Descriptor>
  void operator()(std::ostream& out, Descriptor key) const
  {
    bool first = true;
    for (dynamic_properties::const_iterator i = dp->begin();
         i != dp->end(); ++i) {
      if (typeid(key) == i->second->key()
          && i->first != *node_id) {
        if (first) out << " [";
        else out << ", ";
        first = false;

        out << i->first << "=" << escape_dot_string(i->second->get_string(key));
      }
    }

    if (!first) out << "]";
  }

private:
  const dynamic_properties* dp;
  const std::string* node_id;
};