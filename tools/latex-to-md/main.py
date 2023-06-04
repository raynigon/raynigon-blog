import click
import os
import re
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path

plt.rc('mathtext', fontset='cm')
plt.rcParams['text.usetex'] = True

KNOWN_BLOCKS = ["itemize", "enumerate"]

def latex2svg(equation, filename):
    """
    Turn LaTeX string to an SVG formatted string using the online SVGKit
    found at: http://svgkit.sourceforge.net/tests/latex_tests.html
    """
    if '\\begin' in equation or '\t' in equation:
        with open(filename, 'w') as output_file:
            output_file.write("<!-- TODO manual conversion needed -->\n")
        return
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, r'${}$'.format(equation), fontsize='medium', color='black')

    output = BytesIO()
    fig.savefig(output, dpi=600, transparent=True, format='svg',
                bbox_inches='tight', pad_inches=0.0)
    plt.close(fig)
    output.seek(0)
    with open(filename, 'wb') as output_file:
        output_file.write(output.read())

class Parser:

    def __init__(self, bibtex, citation_count) -> None:
        # State machine with following states:
        # 0: normal mode all text is copied to the output document without modification
        # 1: comment mode all text is ignored until the end of the line
        # 2: command name mode the command is parsed and the output of the command is copied to the output document
        # 3: command argument mode the argument is parsed
        # 90-99: block mode copy
        self.state = 0
        self.bibtex = bibtex
        self.block_type = None
        self.command_name = ""
        self.command_argument_value = ""
        self.command_arguments = []
        self.command_argument_depth = 0
        self.block_copy_mode_depth = 0
        self.enumarate_counter = 0
        self.citation_counter = citation_count
        self.citation_map = {}
        self.citation_map_reverse = {}
        self.parsed = ""
        self.block_buffer = ""
        self.equation_counter = 0

    def write_footer(self)->str:
        output = "\n"
        for k, v in self.citation_map.items():
            output += f"[^{k}]: "
            if "author" in v:
                output += v["author"] + ", "
            if "title" in v:
                output += v["title"] + ", "
            if "year" in v:
                output += v["year"] + ", "
            if "url" in v:
                hostname = v["url"].split('/')[2]
                output += f"[{hostname}]({v['url']})"
            output += "\n\n"
        return output+"\n"

    def next_char(self, c:str)->str:
        self.parsed += c
        output = ""
        if self.state == 0 and c == '#':
            self.state = 1
        elif self.state == 0 and c == '\\':
            self.state = 2
        elif self.state == 0:
            output += c
        elif self.state == 1 and c != '\n':
            pass # Ignore the comments content
        elif self.state == 1 and c == '\n':
            output += '\n'
            self.state = 0
        elif self.state == 2 and c != '{' and c != '['  and c != ' ' and c != '\n':
            self.command_name += c
        elif (self.state == 2 or self.state == 4) and (c == '{' or c == '['):
            self.state = 3
        elif (self.state == 2  and (c == ' ' or c == '\n')) or self.state == 4:
            if self.command_name == "begin" and self.command_arguments[0] not in KNOWN_BLOCKS:
                self.state = 90
                self.block_type = self.command_arguments[0]
                self.block_copy_mode_depth = 1
                self.command_name = ""
                self.command_argument_value = ""
                self.command_arguments = []
                self.block_buffer = ""
                if self.block_type == "equation":
                    output += f'\n<img src="assets/equation_{self.equation_counter}.svg" style="width: 50%;height: auto;padding: 10px;"/>\n'
                else:
                    output += '```latex\n\\begin{' + self.block_type + '}\n'
            else:
                output += self.evaluate()
                self.state = 0
                if len(output) > 0 and output[-1] != '\n':
                    output += c
                self.command_name = ""
                self.command_argument_value = ""
                self.command_arguments = []
        elif self.state == 3 and c != '}' and c != ']':
            self.command_argument_value += c
        elif self.state == 3 and (c == '}' or c == ']'):
            self.command_arguments.append(self.command_argument_value)
            self.command_argument_value = ""
            self.state = 4
        # Block copy mode
        elif self.state == 90 and c != '\\':
            self.block_buffer += c
        elif self.state == 90 and c == '\\':
            self.block_buffer += c
            self.state = 91
        elif self.state == 91 and c != ' ' and c != '\n' and c != '{' and c != '[':
            self.block_buffer += c
            self.command_name += c
        elif self.state == 91 and (c == '{' or c == '['):
            self.block_buffer += c
            self.state = 92
            self.command_argument_depth += 1
        elif self.state == 92 and (c == '{' or c == '['):
            self.block_buffer += c
            self.command_argument_depth += 1
        elif self.state == 92 and (c == '}' or c == ']'):
            self.block_buffer += c
            self.command_argument_depth -= 1
            if self.command_argument_depth <= 0:
                self.state = 91
        elif self.state == 92 and c != '\\':
            self.block_buffer += c
        elif self.state == 92 and c == '\\':
            self.command_name = ""
            self.command_arguments = []
            self.command_argument_depth = 0
            self.block_buffer += c
            self.state = 91
        elif self.state == 91 and (c == ' ' or c == '\n'):
            initial_block_type = self.block_type
            self.block_buffer += c
            if self.command_name == "begin":
                self.block_copy_mode_depth += 1
            elif self.command_name == "end":
                self.block_copy_mode_depth -= 1
            if self.block_copy_mode_depth == 0:
                self.state = 0
                self.block_type = None
                if initial_block_type == "equation":
                    equation = self.block_buffer.removesuffix('\end{equation}\n').replace('\n', ' ')
                    if not os.path.exists("assets"):
                        os.mkdir("assets")
                    latex2svg(equation.strip(), f"assets/equation_{self.equation_counter}.svg")
                    self.equation_counter += 1
                    output += '\n'
                else:
                    output += self.block_buffer
                    output += '```\n<!-- TODO manual conversion needed -->\n'
                self.block_buffer = ""
            else:
                self.state = 90
            self.command_name = ""
            self.command_argument_value = ""
            self.command_arguments = []
        else:
            raise Exception(f"Unknown state {self.state} with character '{c}'")
        return output

    def evaluate(self)->str:
        command_name = self.command_name
        if command_name == "\\":
            return "\n\n"
        if command_name == "par":
            return "\n\n"
        elif command_name == "chapter":
            return "# " + self.command_arguments[0] + "\n"
        elif command_name == "section":
            return "## " + self.command_arguments[0] + "\n"
        elif command_name == "subsection":
            return "### " + self.command_arguments[0] + "\n"
        elif command_name == "subsubsection":
            return "#### " + self.command_arguments[0] + "\n"
        elif command_name == "label":
            return ""
        elif command_name == "cite" and self.bibtex is not None:
            key = self.command_arguments[-1]
            if key in self.citation_map_reverse:
                return f"[^{self.citation_map_reverse[key]}]"
            self.citation_counter+=1
            value = self.bibtex[key]
            self.citation_map[self.citation_counter]=value
            self.citation_map_reverse[key]=self.citation_counter
            return f"[^{self.citation_counter}]"
        elif command_name == "begin":
            if self.block_type is not None:
                raise Exception(f"Nested blocks are not supported. Block type {self.block_type} is already open.")
            self.block_type = self.command_arguments[0]
            self.enumarate_counter = 0
            return "\n"
        elif command_name == "item" and self.block_type == "itemize":
            return "*"
        elif command_name == "item" and self.block_type == "enumerate":
            self.enumarate_counter += 1
            return f"{self.enumarate_counter}."
        elif command_name == "end":
            self.block_type = None
            self.enumarate_counter = 0
            return "\n"
        elif self.block_type is not None:
            return f"\\{command_name}[{']['.join(self.command_arguments)}]"
        else:
            return f"`\\{command_name}[{']['.join(self.command_arguments)}]`"

def parse_bibtex(filename):
    """Parse the bibtex file and return a bibliography object"""
    if filename is None:
        return None
    with open(filename, 'r') as input:
        content = input.read()
    parts = content.split('\n@')[1:]
    bibliography = {}
    for part in parts:
        index_0 = part.find('{')
        index_1 = part.find(',')
        ref_type = part[:index_0]
        ref_key = part[index_0+1:index_1]
        entries = part.splitlines()[1:-1]
        attributes = {}
        for line in entries:
            index_0 = line.find('=')
            key = line[:index_0].strip()
            value = line[index_0+3:].strip()
            if value.endswith('},'):
                value = value[:-2]
            elif value.endswith('}'):
                value = value[:-1]
            attributes[key] = value
        attributes["reference_type"] = ref_type
        bibliography[ref_key] = attributes
    return bibliography


def convert(filename, output, bibtex, citation_count):
    """Convert the latex file to markdown"""
    with open(filename, 'r') as input:
        input_document = input.read()
    # Fix line endings
    input_document = input_document.replace('\r\n', '\n')
    output_document = ""
    
    parser = Parser(bibtex, citation_count)
    for c in input_document:
        output_document += parser.next_char(c)
    output_document += parser.write_footer()
    # Write the output document
    with open(output, 'w') as output:
        output.write(output_document)

def post_process(filename):
    with open(filename, 'r') as input:
        input_lines = input.readlines()
    output = []
    enumeration_pattern = re.compile(r"^\t([0-9]+). (.*)")
    for line in input_lines:
        if line.startswith("\t*"):
            output.append("*"+line.removeprefix("\t*"))
            continue
        enumeration_match = enumeration_pattern.match(line)
        if enumeration_match is not None:
            output.append(enumeration_match.group(1)+". "+enumeration_match.group(2))
            continue
        output.append(line)
    with open(filename, 'w') as out:
        out.writelines(output)
    
@click.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--bibliographie', default=None, help='The file path to the bibtex bibliographie file')
@click.option('--citation_count', default=0, help='The start count for citations')
def main(filename, bibliographie, citation_count):
    """Convert a latex file to a markdown file.
    
    filename is the latex file to convert.
    """
    filepath = Path(filename)
    os.chdir(filepath.parent.absolute())
    
    bibtex = None
    if bibliographie is not None:
        bibtex = parse_bibtex(bibliographie)
    output = filename.replace('.tex', '.md')
    convert(filename, output, bibtex, citation_count)
    post_process(output)


if __name__ == '__main__':
    main()