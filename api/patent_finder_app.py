from fastapi import FastAPI
from pydantic import BaseModel
from lib import patent_finder as pf
app = FastAPI()

PF = pf.PatentFinder()

class Input(BaseModel):
    file_path: str
        
@app.put("/find-patents-links-from-doc")
def get_patents_links_from_doc(d:Input):
    
    return PF.get_patents_links_from_pdf(d.file_path)

@app.put("/find-patents-details-from-doc")
def get_patents_all(d:Input):
    
    return PF.get_patents_links_from_pdf(d.file_path, links_only_flag=False)
    
@app.put("/find-patents-links-from-similar")
def get_patents_from_similar(d:Input):
    
    similar_doc = PF.get_similar_docs_from_es(d.file_path, top_n=1)[0]
    return PF.format_result(similar_doc)

@app.put("/find-patents-links")
def get_patents_links(d:Input):
    
    return PF.get_patents_links(d.file_path)

@app.put("/find-similar-docs")
def get_similar_docs(d:Input):
    
    return PF.get_similar_docs_from_es(d.file_path)