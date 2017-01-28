# patrom

patrom is a web templating system, with Python code inserted inside HTML pages.

The engine uses the custom HTML tag `<py>`, and a custom HTML attribute `attrs`.

To insert a block of code, for instance a `for` loop or a condition, the 
syntax is :

```xml
<py code="for i in range(10):">
   ...
</py>
```

`elif` and `else` keywords must be inserted with their own `<py>` tag :

```xml
<py code="if condition:">
  ...
</py><py code="elif condition2:">
  ...
</py>
```

For a statement, also use the attribute `code` inside a "start/end" tag, ie
a tag that ends with `/>` :

```xml
<py code="x = 5"/>
```

To insert the result of an expression, use the attribute `expr` of tag `<py>`:

```xml
<py expr="month"/>
<py expr="'red' if condition else 'blue'"/>
```

To set attributes of other HTML tags, set an attribute `attrs` holding key /
value pairs as in keyword arguments of Python functions :

```xml
<input attrs="value=name">
```

For attributes that don't have values, the value associated with the key
must be a boolean ; if it is set to `True` the attribute is set, if it is
`False` it is ignored :

```xml
<option attrs="selected=value==expected"/>
```
