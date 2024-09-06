import os
import uvicorn

from db.mongo import MongoDB
from db.pinecone import PineConeDB
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from io import BytesIO
from pydantic import BaseModel
from typing import Optional
from utils import parser

app = FastAPI()
pinecone_db = PineConeDB.instance()
model = SentenceTransformer('all-MiniLM-L6-v2')

html_directory = "frontend"

# Middleware to allow connections from React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    load_dotenv()
    MongoDB.initialize()

# Building hebbia
# https://a16z.com/announcement/investing-in-hebbia/
"""
1) Parse input of a query
2) Choose a list of relevant documents (aka rows) by querying pinecone 
3) Generate a list of relevant datapoints (aka columns) by asking OpenAI's GPT-3
    - consider hardcoding some defaults like date, document type, summary, etc.
4) Save the CSV file somewhere in the cloud, along with the original query and timestamp
5) Build a React UI that will take in to 2d array of rows and columns and display it in a human readable table format
"""

# Technically this should probably be a post endpoint but easier for debugging if we make it a GET
@app.get("/clear")
async def clear():
    collection = MongoDB.get_collection("hebbia", "documents")
    collection.delete_many({})
    pinecone_db.pc.delete_index("docs-index")
    return "All documents deleted"

@app.get("/filters")
async def get_filters():
    collection = MongoDB.get_collection("hebbia", "documents")
    filters = {
        "companies": collection.distinct("company"),
        "filings": collection.distinct("filing_type"),
    }
    return JSONResponse(filters)

class Query(BaseModel):
    query: str
    companies: Optional[list[str]] = []
    minimum_date: Optional[int] = None
    maximum_date: Optional[int] = None
    filings: Optional[list[str]] = []

@app.get("/search", response_class=HTMLResponse)
async def render_search_form():
    file_path = os.path.join(html_directory, "search.html")
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return HTMLResponse(content=content)

# TODO?(JSHU): Given a user query, produce a set of key/value pairs to automatically filter on
# This is likely going to involve a separate endpoint that fires at the same time as the /search endpoint

@app.post("/search")
async def search(query: Query):
    print("Received query:", query)
    # TODO?(JSHU): Use a generative model to rephrase a query to be optimize for retrieval (ask llm to rephrase)
    # Could also extract company and filing filters from the query phrase and use that to filter the search
    filters = {}
    if query.filings:
        filters["filing_type"] = {"$in": query.filings}
    if query.companies:
        filters["company"] = {"$in": query.companies}
    if query.minimum_date and query.maximum_date:
        filters["date"] = {"$gte": query.minimum_date, "$lte": query.maximum_date}
    results = [["Content", "Score", "Date", "Company", "Filing Type"]]
    matches = pinecone_db.query_docs(query.query, 3, filters)
    for match in matches["matches"]:
        score, metadata = match['score'], match['metadata']
        if score < 0.2:
            break
        content, date = metadata['original_text'], metadata['human_readable_date']
        company, filing_type = metadata['company'] , match['metadata']['filing_type']
        next_row = [content, score, date, company, filing_type]
        results.append(next_row)
    return JSONResponse(content={"result": results})

@app.get("/process")
async def process():
    num_files = 0
    num_folders = 0
    directory = "data"
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)    
        if os.path.isdir(file_path):
            print(f"Processing folder: {file_path}")
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                print(f"Processing file: {file_path}")
                # TODO(JSHU): Parse files in folders recursively
                num_files += 1
            num_folders += 1
        elif os.path.isfile(file_path):
            print(f"Processing file: {file_path}")
            parser.html_parser(file_path)
            num_files += 1
    return f"Processed {num_files} files and {num_folders} folders"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)