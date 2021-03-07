from google_patent_scraper import scraper_class
from sentence_transformers import SentenceTransformer
import re
import json
import requests
import sys, os, contextlib
from lib.utils import *

#TODO: create class to safely interact with config
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(THIS_FOLDER, 'config.json')
Config = json.load(open(config_file_path, 'r'))
COUNTRY_CODES = Config['RegEx']['COUNTRY_CODES']


class ElasticSearch:
    def __init__(self):
        self.headers = {'Authorization': Config['Elasticsearch']['Authorization'], 'Content-Type': Config['Elasticsearch']['Content-Type']}

    def search(self, index, payload):
        search_url = Config['Elasticsearch']['Host'] + index + "/_search"
        response = requests.post(search_url, headers=self.headers, json=payload)
        return response.json()
    
    def fetch_samples(self, payload):
        response = self.search('fr_dtj_cir', payload)
        return response['hits']['hits']


class PatentFinder:
    """Class for Patent Number extraction."""
    
    def __init__(self):
        """Create an instance from the class."""
        self.PATENT_NUMBER_REGEX = r"(?<![^ |°|#|/|=:])(?P<authority>"+COUNTRY_CODES+r")\s*?(?P<number>\d{3,11}|(?:(?:Patents?|Pat\.?) )?(?:(?:Numbers?|Nos?\.?) ?)?(?:(?:# ?)?\d[,.']?)\d\d\d[,.']?\d\d\d[,.' ]?)\s?(?P<kind>\(?[A-Z](?![a-zA-Z])[0-9]?\)?)?"
        self.es = ElasticSearch()
        self.model = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        self.model.max_seq_length = 510
    
    def get_patents_refs(self, content):
        # ~ Clean input content
        clean_content = clean_str(content)
        # ~ Get all patents in contnet
        matches = re.findall(self.PATENT_NUMBER_REGEX, clean_content)
        # ~ Join Regex groups as one patent number and remove duplicates
        patents_list_raw = list(set(["".join(patent_number) for patent_number in matches]))
        # ~ Remove () from patents numbers if exist
        patents_list = [re.sub(r'[(,.)\' ]|Patents?|Pat\.?|Numbers?|Nos?\.?', '', patent_number) for patent_number in patents_list_raw]
        return patents_list
    
    def get_patents_from_content(self, content, links_only_flag=True):
    
        # ~ Get list of referenced patents
        patents_list = self.get_patents_refs(content)

        # ~ Init scraper class
        scraper=scraper_class() 

        # ~ Add patents to list
        for patent_number in patents_list:
            scraper.add_patents(patent_number)

        # ~ Scrape all patents
        if scraper.list_of_patents:
                with open(os.devnull, "w") as f, contextlib.redirect_stdout(f): #Safely disabling indesirable prints from this function
                    scraper.scrape_all_patents()

        # ~ Isolate not found patents
        not_found_patents = []
        for patent_number in scraper.list_of_patents[:]:
            if not scraper.parsed_patents[patent_number]:
                not_found_patents.append(patent_number)
                scraper.delete_patents(patent_number)
                del scraper.parsed_patents[patent_number]

        result = {}
        if links_only_flag:
            # ~ Return patents links
            result["in_google_patent"] = [{"patent_number":patent_number, "patent_url":patent_number_details["url"] } for (patent_number, patent_number_details) in scraper.parsed_patents.items()]
        else:
            # ~ Return parsed patents details
            result["in_google_patent"] = scraper.parsed_patents

        result["not_in_google_patent"] = not_found_patents
        return result

    def get_patents_links_from_pdf(self, file_path, links_only_flag = True):

        # ~ Get content from PDF
        content = pdf2raw(file_path)
        return self.get_patents_from_content(content, links_only_flag)

    def encode_content(self, text_chunks):
        # ~ Return the encoded text formatted for ES
        return self.model.encode(text_chunks).mean(axis=0)[:500].tolist()

    def get_similar_docs(self, content, top_n = 5):

        # ~ get meaningful content i.e. research related
        meaningful_text_chunks = extract_meaningful_text(content)
        if meaningful_text_chunks:
            # ~ Encode the content:
            meaningful_content_vector = self.encode_content(meaningful_text_chunks)

            # ~ run query against ES

            similar_payload = {
                "size": 100,
                "_source": [
                    "documentTitle",
                    "patents"
                ],
                "query": {
                    "script_score": {
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "exists": {
                                            "field": "meaningful_content_vector"
                                        }
                                    },
                                    {
                                        "exists": {
                                            "field": "patents"
                                        }
                                    }
                                ]
                            }
                        },
                        "script": {
                            "source": "cosineSimilarity(params.queryVector, doc['meaningful_content_vector']) + 1.0",
                            "params": {
                                "queryVector": meaningful_content_vector
                            }
                        }
                    }
                }
            }

            similar_docs = self.es.fetch_samples(similar_payload)

            return similar_docs[0:top_n]
        else:
            return []

    def get_similar_docs_from_es(self, file_path, top_n=5):

        # ~ Get content from PDF
        content = pdf2raw(file_path)
        return self.get_similar_docs(content, top_n)

    def get_patents_from_similar_doc(self, content):

        # ~ Get the most similar doc
        similar_doc = self.get_similar_docs(content, top_n=1)[0]

        # ~ return patents from most similar
        return self.format_result(similar_doc)

    def format_result(self, similar_doc):
        return {"patents": similar_doc['_source']['patents'],
                "from_document": similar_doc['_source']['documentTitle'],
                "similarity_score": similar_doc["_score"]}
    
    def get_patents_links(self, file_path):

        # ~ Get content from PDF
        content = pdf2raw(file_path)

        # ~ Check if the document has petents mentions
        result = self.get_patents_from_content(content)

        # ~ Otherwise, get patents from the similar docs
        if not result['in_google_patent']:
            result = self.get_patents_from_similar_doc(content)
        return result