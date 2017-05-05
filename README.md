# patrom

patrom is a web templating system, with Python code inserted inside HTML pages.

Templates syntax
================

The engine uses the custom HTML tag `<py>`, and a custom HTML attribute `attrs`.

Code blocks
-----------
To insert a code block (loop or condition), the syntax is :

```xml
<py code="for i in range(10):">
   ... code block ...
</py>
```

`elif` and `else` keywords must be inserted with their own `<py>` tag :

```xml
<py code="if condition:">
  ...
</py>
<py code="elif condition2:">
  ...
</py>
<py code="else:">
  ...
</py>
```

`break` and `continue` can be used inside loops :

```xml
<py code="for i in range(10):">
    <py code="if i == 5:">
        <py code="break" />
    </py>
</py>

```

Note the use of a self-closing tag (ending with `/>`) for these keywords.

Statements and expressions
--------------------------

For a statement, also use the attribute `code` inside a self-closing tag:

```xml
<py code="x = 5" />
```

To insert the result of an expression, use the attribute `expr`:

```xml
<py expr="month" />
<py expr="'red' if condition else 'blue'" />
```

Tag attributes
--------------
To set attributes of other HTML tags, use the attribute `attrs` holding key /
value pairs as in keyword arguments of Python functions :

```xml
<input attrs="value=name, id=record_id">
```

For attributes that don't have values, the value associated with the key
must be a boolean ; if it is set to `True` the attribute is set, if it is
`False` it is ignored :

```xml
<option attrs="selected=value==expected">
```

Including templates
-------------------
A template can be included inside another one :

```xml
<py include="header.html" />
```

Using the patrom module
=======================

Installation
------------
```
pip install patrom
```

Rendering templates
-------------------
```python
import patrom
patrom.render(filename, **kw)
```
renders the template file at location `filename` with the keyword arguments
`kw`. The keys in `kw` are used as the namespace for the template.

For instance, if the template file __hello.html__ is

```xml
Hello <py expr="name" /> !
```

the result of
```python
patrom.render("hello.html", name="World")
```
is
```
Hello World !
```

If a template includes another one, the included template is rendered with the
same keys / values.
