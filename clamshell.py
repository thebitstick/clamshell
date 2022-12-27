import subprocess
import os
import pandas as pd
import glob
import sys
import time
import traceback
from pygments.lexers.python import PythonLexer
from rich import print
from prompt_toolkit import prompt, print_formatted_text, PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console

def try_else_none(function):
    def wrapped_function(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except:
            return None
    return wrapped_function

class ClamShell:
    def __init__(self, super_commands: list):
        self.splitter = self.get_splitter()
        self.console = Console(color_system='auto')
        self.super_commands = super_commands
        self.lexer = PygmentsLexer(PythonLexer)
        self.globals = globals()
        self.locals = locals()
        self.session = PromptSession()

    def get_splitter(self):
        if os.name == 'nt':
            return '\\'
        return '/'

    @try_else_none
    def get_created_datetime(self, file):
        created = os.path.getctime(file)
        created = time.ctime(created)
        return created

    @try_else_none
    def get_modified_datetime(self, file):
        modified = os.path.getmtime(file)
        modified = time.ctime(modified)
        return modified

    def get_type(self, file):
        if os.path.isfile(file):
            return 'file'
        else:
            return 'directory'

    def files(self, path=None, recursive=False):
        cwd = os.getcwd()
        if path is None:
            path = '**'
        elif path[-1] == self.splitter:
            path += '**'
        elif path [-1] != '*':
            path += f'{self.splitter}**'
        file_info = [{
            'name': i,
            'path': f'{cwd}{self.splitter}{i}',
            'created': self.get_created_datetime(i),
            'modified': self.get_modified_datetime(i),
        } for i in glob.glob(path)]
        return file_info

    def goto(self, path='.'):
        if isinstance(path, dict):
            os.chdir(path['path'])
            return
        os.chdir(path)

    def get_prompt(self):
        cwd = os.getcwd()
        return f" 🐚 {cwd} $ "

    def with_quotes_if_undefined(self, string):
        try:
            exec(string)
            return string
        except:
            return f'"{string}"'

    def flatten_list(self, list_of_lists):
        return [item for sublist in list_of_lists for item in sublist]

    def break_into_pieces(self, string):
        pieces = string.split("'")
        pieces = self.flatten_list([i.split('"') for i in pieces])
        pieces = [i.replace('"', '').replace("'", '') for i in pieces]
        pieces = [i.strip() for i in pieces]
        pieces = [i for i in pieces if i != '']
        pieces = [self.with_quotes_if_undefined(i) for i in pieces]
        remade = f'{pieces[0]}({", ".join(pieces[1:])})'
        print(remade)
        return remade

    def python_exec(self, command: str):
        try:
            output = eval(command, self.globals, self.locals)
            return output
        except:
            return exec(command, self.globals, self.locals)

    def clam_exec(self, command: str):
        reformed = self.break_into_pieces(command)
        return self.python_exec(reformed)

    def shell_exec(self, command: str):
        subprocess.call(command)
        return None

    def super_exec(self, command: str):
        assert len(command.strip().split(' ')) == 1
        command += '()'
        return self.python_exec(command)

    def try_except_chain(self, try_list: list, first_exception=None):
        """
        try except for everything in list,
        list must be series of no_argument functions
        capture and return first exception if no pass
        """
        if len(try_list) == 0:
            return first_exception
        to_try = try_list[0]
        try:
            return to_try()
        except Exception as e:
            try:
                message = e.message
            except AttributeError:
                message = ''
            if first_exception is None:
                first_exception = ' ! >> ' + str(repr(e))
            return self.try_except_chain(try_list[1:], first_exception)

    def repl_loop(self):
        command = self.session.prompt(
            self.get_prompt(),
            lexer=self.lexer,
            auto_suggest=AutoSuggestFromHistory(),
        )
        if command in self.super_commands:
            result = self.super_exec(command)
        else:
            result = self.try_except_chain([
                lambda: self.python_exec(command),
                lambda: self.clam_exec(command),
                lambda: self.shell_exec(command),
            ])
        if result is not None:
            self.console.print(result)

# making callable function
app = ClamShell(['files'])
def files(*args, **kwargs):
    return app.files(*args, **kwargs)

def goto(*args, **kwargs):
    return app.goto(*args, **kwargs)
while True:
    app.repl_loop()