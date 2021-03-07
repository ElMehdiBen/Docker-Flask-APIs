import re
import unicodedata
import difflib
from tika import parser


unwanted_sections = [
    'L’ENTREPRISE',
    'CONTEXTE FISCAL',
    'CONTEXTE CIR',
    'CONTEXTE CII',
    'INSERTION DES PROJETS DANS LA STRATEGIE DE L’ENTREPRISE',
    'ACTIVITES DE R&D ET D’INNOVATION',
    'INCERTITUDES SCIENTIFIQUES ET TECHNIQUES',
    'INCERTITUDES TECHNIQUES ET SCIENTIFIQUES',
    'ALEAS, INCERTITUDES SCIENTIFIQUES',
    'RESSOURCES HUMAINES',
    'PARTENARIAT SCIENTIFIQUE ET RECHERCHE CONFIEE',
    'PRESENTATION DE LA SOCIETE',
    'PRESENTATION DES ACTIVITES DE R&D',
    'LA SOCIETE DANS LE DISPOSITIF DU CIR',
    'MONTANT DU CIR',
    'REPARTITION DU PERSONNEL SUR LES PROJETS',
    'DOTATIONS AUX AMORTISSEMENTS',
    'DEPENSES DE PERSONNEL',
    'DEPENSES DE VEILLE TECHNOLOGIQUE',
    'DEPENSES DE SOUS‐TRAITANCE',
    'SUBVENTIONS',
    'AVANCES REMBOURSABLES',
    'FRAIS DE PRISE ET MAINTENANCE DE BREVETS',
    'FEUILLETS CERFA',
    'CV ET DIPLOMES DU PERSONNEL VALORISE DANS LE CALCUL DU CIR',
    'TABLEAU SYNTHETIQUE DES OPERATIONS DE R&D',
    'REFERENCES BIBLIOGRAPHIQUES',
    'ACQUISITION DE CONNAISSANCES',
    'ORGANISMES PUBLICS SANS LIEN DE DEPENDANCE'
]
"""padding """
unwanted_sections = [" . "+x for x in unwanted_sections]
unwanted_sections = unwanted_sections + [" ."+x for x in unwanted_sections]


## Read pdf
def pdf2raw(file_path):
    raw = parser.from_file(file_path)
    return raw['content']

## Cleaning functions
def remove_NBS(content):
    #remove non breaking spaces 
    return content.replace("\xa0"," ")

def remove_newline(content):
    #remove newline
    return content.replace("\n"," ")

def is_pua(c):
    #helper function for remove_PUA() 
    return unicodedata.category(c) == 'Co'

#is_pua('\uf0b7')

def remove_PUA(content):
    #remove Private Use Areas unicodes
    return "".join([char for char in content if not is_pua(char)])
    #this regex is working but not in python, need to investigate
    #return re.sub(r'\\u[e-f][0-9a-z]{3}', '', content)

def remove_widespace(content):
    #remove newline
    #return " ".join(content.split())
    return '\n'.join(' '.join(line.split()) for line in content.split('\n'))

def remove_extra_dots(content):
    #remove extra dots
    return content.replace("..","")

#big girl of a cleaning function
def clean_str(content):
    return remove_NBS(
                remove_widespace(
                    remove_newline(
                        remove_PUA(
                            remove_extra_dots(
                                content
                            )))))

def clean_str_keep_lines(content):
    return remove_NBS(
                remove_widespace(
                    remove_PUA(
                        remove_extra_dots(
                            content
                        ))))

### Related to extracting meeaningful parts

def remove_small_blocks(lines, min_size):
    #Remove small blocks
    return [x for x in lines if len(x)> min_size]

def remove_spaces(text):
    #remove all spaces
    return "".join(text.split())

def similar(a, b, remove_whitespace=True):
    """
    Example:
    >> a = "REPARTITION DU PERSONNEL SUR LES PROJETS"
    >> b = "2. REPARTITION DU PERSONNEL SUR LES PROJETS PROJETS R&D 2011 PC B "
    >> similar(a, b[:40])
    0.927536231884058
    """
    a, b = list(map(lambda x: str.lower(x), [a,b]))
    if remove_whitespace:
        a, b = list(map(lambda x: remove_spaces(x), [a,b]))
        return difflib.SequenceMatcher(None, a[:len(b)], b).quick_ratio()
    else:
        return difflib.SequenceMatcher(None, a[:len(b)], b).quick_ratio()

def content2lines(content):
    #Returns the doc raw content cleaned and broken to lines
    return [s for s in clean_str_keep_lines(content).splitlines() if s]

def dedupe_lines(content_lines):
    #Remove duplicate lines and close matches
    #TODO: This one takes time and should be optimized
    deduped_lines = [] 
    [deduped_lines.append(x) if starts_with_para_number(x) else deduped_lines.append(x) if not difflib.get_close_matches(x, deduped_lines, cutoff=0.75) else '' for x in content_lines]
    return deduped_lines

def starts_with_para_number(line):
    #This function checks if we're dealing with a start of section
    return bool(re.match('([1-9] ?\.)|(^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3}) ?\.)',line))

def assemble_by_section(deduped_lines):
    #virtually assemble the sections
    assembled_sections = []
    for line in deduped_lines:
        if starts_with_para_number(line):
            assembled_sections.append(line)
        elif assembled_sections:
            assembled_sections[-1] = assembled_sections[-1] +" "+line
    return assembled_sections

def remove_unwanted_sections(meaningful_text):
    real_meaningful_content = [x for x in meaningful_text 
     if max([similar(x[:len(unwanted_section)+30], unwanted_section) for unwanted_section in unwanted_sections]) < 0.85]
    return real_meaningful_content

def break_to_chunks(content, chunk_size):
    chunks = []
    for e in content:
        tokens = e.split()
        if len(tokens) > chunk_size:
            for chunk in [tokens[x:x+chunk_size] for x in range(0, len(tokens), chunk_size)]:
                chunks.append(" ".join(chunk))
        else:
            chunks.append(e)
    return chunks

def extract_meaningful_text(content):
    #Returns the doc raw content cleaned and broken to lines
    content_lines = content2lines(content)
    del content
    #Remove duplicate lines and close matches
    deduped_lines = dedupe_lines(content_lines)
    del content_lines
    #virtually assemble the sections
    assembled_sections = assemble_by_section(deduped_lines)
    del deduped_lines
    #Removing small blocks
    assembled_sections = remove_small_blocks(assembled_sections, 250)
    #remove the sections that are irrelevent
    real_meaningful_content = remove_unwanted_sections(assembled_sections)
    del assembled_sections
    #Breaking to chunks for Bert
    real_meaningful_content_chunked = break_to_chunks(real_meaningful_content, 350)
    del real_meaningful_content
    return real_meaningful_content_chunked