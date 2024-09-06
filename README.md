### run app locally

uvicorn main:app --host 0.0.0.0 --reload --port 80

### test search endpoint output

curl -X 'POST' \
  'http://localhost:8000/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"text": "We are meeting the management team of Apple tomorrow. Draft a DD agenda based on your assessment of their key documents.", "companies" ["Apple Inc.", "Salesforce, Inc."],}'

### generate requirements.txt

pipreqs . --force

### setting up env variable on heroku
heroku config:set PINECONE_API_KEY=your-api-key

