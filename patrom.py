import os
import sys
import io
import tokenize
import traceback
import random
import string

import html.parser

class TemplateError(Exception):

    def __init__(self, msg, parser, text):
        self.msg = msg
        self.line, self.column = parser.getpos()
        self.text = text

    def __str__(self):
        return '{} line {}'.format(self.msg, self.line)


class TemplateParser(html.parser.HTMLParser):

    forbidden = ['import', 'exec', '__builtins__', '__import__']
    PY_TAG = 'py'

    def __init__(self, *args, **kw):
        kw.setdefault('convert_charrefs', True)
        try:
            html.parser.HTMLParser.__init__(self, *args, **kw)
        except TypeError:
            # convert_charrefs is only supported by Python 3.4+
            del kw['convert_charrefs']
            html.parser.HTMLParser.__init__(self, *args, **kw)
            
        self.src = '' # Generated Python source code
        self.indent = 0
        self.py_tags = [] # stack of Python blocks
        self.pyline = 0 # line number in generated Python code
        self.line_mapping = {} # maps Python line num to template line num

    def _randname(self):
        return ''.join(random.choice(string.ascii_letters) for i in range(8))
        
    def add(self, source, text):
        line, column = self.getpos()
        self.src += self.indent*'    '+source+'\n'
        self.pyline += 1+source.count('\n')
        self.line_mapping[self.pyline] = (line, column, text)
    
    def control(self, source, text):
        """Control that Python source code doesn't include sensible
        names"""
        reader = io.BytesIO(source.encode('utf-8')).readline
        for tok_type, tok, *args in tokenize.tokenize(reader):
            if tok_type == tokenize.NAME:
                if tok in self.forbidden:
                    msg = 'forbidden name "{}"'
                    raise TemplateError(msg.format(tok), self, text)
        
    def handle_starttag(self, tag, attrs):
        """Handle a start tag
        If tag is PY_TAG :
        - add its attribute "code" to generated source code
        - if the code starts a block (ie ends with ":"), increment indentation.

        Else print the tag, formatted by method _format()
        """
        text = self.get_starttag_text()
        line, column = self.getpos()
        if tag == self.PY_TAG:
            for name, value in attrs:
                if name=='code':
                    has_code = True
                    value = value.rstrip()
                    self.control(value, text)
                    self.add(value, text)
                    self.py_tags.append([value, self.get_starttag_text(), 
                        (line, column)])
                    if value.endswith(':'):
                        self.indent += 1
                    break
                elif name=='expr':
                    raise TemplateError("attribute expr is only supported"
                        " in start/end tags, not in start tags", self, text)
                else:
                    msg = 'unknown attribute "{}"'
                    raise TemplateError(msg.format(name), self, text)
            else:
                msg = 'py tag missing attribute "code"'
                raise TemplateError(msg, self, text)
        else:
            self.handle_attrs(tag, attrs, text)

    def handle_startendtag(self, tag, attrs):
        """Handle a startend tag, ie a tag ending with />"""
        text = self.get_starttag_text()
    
        if tag == self.PY_TAG:
            # tags of the form <py ... /> support 2 attributes :
            # - <py code="..."> : the code is added to the source
            # - <py expr="..."> : the result of print(expr) is added to the
            #   source
            line, column = self.getpos()
            has_expr = False
            for name, value in attrs:
                if name=='code':
                    has_expr = True
                    value = value.rstrip()
                    self.control(value, text)
                    if value.endswith(':'):
                        msg = 'A single py tag cannot start a code block : {}'
                        raise TemplateError(msg.format(text), self, text)
                    self.add(value, text)
                elif name == 'expr':
                    has_expr = True
                    value = value.strip()
                    self.add('print({}, end="")'.format(value), text)
                elif name == 'include':
                    has_expr = True
                    path = os.path.join(os.path.dirname(self.filename), 
                        value.strip())
                    res = TemplateParser().render(path, **self.kw)
                    if value.strip()=='header.html':
                        with open('trace_header.py', 'w', encoding='utf-8') as out:
                            out.write(res)
                    self.add('print("""{}""", end="")'.format(res), text)
                else:
                    msg = 'unknown attribute "{}" - use "code"'
                    raise TemplateError(msg.format(name), self, text)
            if not has_expr:
                msg = 'py/ tag missing attribute "code" or "expr"'
                raise TemplateError(msg, self, text)

        else:
            self.handle_attrs(tag, attrs, text)

    def handle_endtag(self, tag):
        text = '</{}>'.format(tag)
        if tag == self.PY_TAG:
            if not self.py_tags:
                msg = 'unexpected closing tag </py>'
                raise TemplateError(msg, self, text)
            value, text, pos = self.py_tags.pop()
            if value.endswith(':'):
                self.indent -= 1
        else:
            self.add('print("{}")'.format(text), text)

    def handle_data(self, data):
        """Data is printed unchanged"""
        if data.strip():
            self.add('print("""{}""", end="")'.format(data), data)     

    def handle_decl(self, decl):
        """Declaration is printed unchanged"""
        self.add('print("""<!{}>""")'.format(decl), decl)     

    def handle_attrs(self, tag, attrs, text):
        """Used for tags other than <py> ; if they have an attribute named 
        "attrs", its value must be of the form key1=value1, key2=value2... ; 
        this value is used as argument of dict(), and the resulting dictionary 
        is used to generate tag attributes "key1=value1 key2=value2 ...".
        If the value associated with a key is True, only the key is added
        (eg selected=True) ; if it is False, the key is ignored"""
        
        if not 'attrs' in [name for (name, value) in attrs]:
            self.add('print("""{}""", end="")'.format(text), text)
            return
        
        # print tag and key/values except for key=='attrs'
        txt = '<{} '.format(tag)
        simple = ['{}=\\"{}\\"'.format(name, value.replace("'", "\\'"))
            for (name, value) in attrs if name !='attrs']

        txt += ' '.join(simple)
        
        self.add('print("{}", end="")'.format(txt), text)
        
        for name, args in attrs:
            if name == 'attrs':
                key_name = 'key_{}'.format(self._randname())
                value_name = 'value_{}'.format(self._randname())
                self.add('for {}, {} in dict({}).items():'.format(key_name, 
                    value_name, args), text)
                self.add('    if not isinstance({}, bool):'.format(value_name), text)
                self.add('        print("{{}}=\\"{{}}\\" ".format({}, {}),'
                    ' end=" ")'.format(key_name, value_name), text)
                self.add('    elif {}:'.format(value_name), text)
                self.add('        print("{{}}".format({}), end=" ")'.format(key_name), text)

        # close tag
        self.add('print(">", end="")', text)

    def render(self, filename, **kw):
        """Renders the template located at templates/<filename>
        
        Returns (status, result) where status is 0 if an exception was raised,
        1 otherwise and result is a string with the error message of the
        template render with key/values in kw
        """
        
        self.filename = filename
        self.kw = kw

        def _debug():
            """Returns formatted error traceback with the line in template"""
            # store original traceback
            out = io.StringIO()
            traceback.print_exc(file=out)
            
            # add line in original template file
            tb = sys.exc_info()[2]
            extract = traceback.extract_tb(tb)
            
            if isinstance(exc, TemplateError):
                line, column, text = exc.line, exc.column, exc.text
            else:
                if isinstance(exc, (SyntaxError, IndentationError)):
                    python_line = sys.exc_info()[1].args[1][1]
                else:
                    python_line = extract[-1][1]
            
                while python_line and python_line not in self.line_mapping:
                    python_line -= 1
                line, column, text = self.line_mapping[python_line]
            out.write('\nLine {} in template {}\n'.format(line, filename))
            out.write(text)
            return out.getvalue()

        # the generated Python code uses "print" to produce the result, so we
        # redirect sys.stdout
        save_stdout = sys.stdout
        
        # get template source code
        with open(filename, encoding="utf-8") as fobj:
            tmpl_source = fobj.read()
        
        try:
            self.feed(tmpl_source)
            self.close()
            
            if self.py_tags: # unclosed <py> tags
                value, text, (line, column) = self.py_tags.pop()
                msg = "Unclosed py tag line {} column {} : {}"
                raise TemplateError(msg, self, text)
        
            sys.stdout = io.StringIO() # redirect sys.stdout
            
            trace = 'trace.py'
            with open(trace, 'w', encoding='utf-8') as out:
                out.write(self.src)
                out.write(str(kw))
            res = exec(self.src, kw)
            return sys.stdout.getvalue()

        except Exception as exc:
            message = _debug()
            print('error message', message, '--end of error message')
            raise TemplateError(message, self, tmpl_source)

        finally:
            sys.stdout = save_stdout
        
        
def render(filename, **kw):
    return TemplateParser().render(filename, **kw)
    