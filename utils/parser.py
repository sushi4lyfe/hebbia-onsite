import re
import uuid

from bs4 import BeautifulSoup
from datetime import datetime
from db.mongo import MongoDB
from db.pinecone import PineConeDB
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
pinecone_db = PineConeDB.instance()

def get_metadata_from_filename(filename):
    pattern = r"(?P<company>.+?) \| (?P<filing>\w+-\w+)\/?A? \((?P<date>.+?)\)\.html"
    # Use re.match to apply the pattern
    match = re.match(pattern, filename)
    metadata = {'filename': filename}
    if match:
        metadata['company'] = match.group("company")
        metadata['filing_type'] = match.group("filing")
        metadata['human_readable_date'] = match.group("date")
        date_object = datetime.strptime(match.group("date"), "%B %d, %Y")
        metadata['date'] = str(int(date_object.timestamp()))
        metadata['filename'] = filename
    print(f"Saved metadata {metadata} to mongodb")
    return metadata

def html_parser(filename, html_content):
    metadata = get_metadata_from_filename(filename)
    mongo_collection = MongoDB.get_collection("hebbia", "documents")
    if mongo_collection.count_documents({"filename": metadata['filename']}) > 0:
        print(f"File {metadata['filename']} has already been parsed")
        return
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    # Detect tables in data and store 
    table_data = extract_table_data(soup)
    for table in table_data:
        insert_table_to_pinecone(table, metadata)
    # Remove table elements to make sure we don't reprocess the table data
    for t in soup.find_all('table'):
        t.decompose()
    text = soup.get_text(separator=' ', strip=True)
    entries = []
    # Splits with newlines may be too long
    for text_chunk in re.split('; |\. |, |_____|\*|\n', text):
        # Remove leading/trailing whitespaces
        cleaned_text = text_chunk.strip()
        if cleaned_text:
            vector = model.encode(f'{cleaned_text} related to company {metadata["company"]} on {metadata['human_readable_date']}')
            unique_id = str(uuid.uuid4())
            metadata['original_text'] = cleaned_text
            metadata['_id'] = unique_id
            entries.append((unique_id, vector.tolist(), metadata))
        if len(entries) >= 100:
            # Insert into Pinecone and print results
            results = pinecone_db.index.upsert(vectors=entries)
            print(f"Results of pinecone insertion in html_parser: {results}")
            entries = []
    try:
        results = pinecone_db.index.upsert(vectors=entries)
        print(f"Results of pinecone insertion in html_parser: {results}")
    except Exception as e:
        print(f"Error inserting entries into pinecone in html_parser {e}")
        return
    mongo_collection.insert_one(metadata)

def extract_table_data(soup):
    # Find all tables in the HTML
    tables = soup.find_all('table')
    all_tables_data = []

    # Iterate over each table
    for table in tables:
        table_data = []
        # Find all rows in the table
        rows = table.find_all('tr')
        for row in rows:
            row_data = []
            # Find all cells within the row (th or td)
            for cell in row.find_all(['th', 'td']):
                row_data.append(cell.text.strip())  # Extract text and remove surrounding whitespace
            table_data.append((row_data))
        all_tables_data.append(table_data)
    return all_tables_data

def insert_table_to_pinecone(table, metadata):
    # Extract column names and row names
    column_names = table[0][1:]  # Skip the first element of the first row
    entries = []

    # Process each row in the table
    for row in table[1:]:  # Skip the first row (header)
        row_name = row[0]   # First element of each row is the row name
        for ind, val in enumerate(row[1:]):     # Rest of the elements are data
            # Create a combined text from row name and data for vectorization
            column_name = ""
            try:
                column_name = column_names[ind+1]
            except:
                continue
            if column_name == "" or row_name == "" or val == "":
                continue
            combined_text = f'The value {column_name} for {row_name} is {val}'
            metadata['original_text'] = combined_text
            vector = model.encode(combined_text)  # Generate the vector
            # Prepare entry for Pinecone insertion
            unique_id = str(uuid.uuid4())
            metadata['_id'] = unique_id
            entries.append((unique_id, vector.tolist(), metadata))
    if entries != []:
        # Insert into Pinecone and print results
        results = pinecone_db.index.upsert(vectors=entries)
        print(f"Results of pinecone insertion in insert_table_to_pinecone: {results}")