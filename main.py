from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pdfplumber
import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import google.generativeai as genai
import re

app=FastAPI()
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
     allow_headers=["*"],
     allow_methods=["*"],
      allow_credentials=True)
genai.configure(api_key="Your_API_Key")
gemini = genai.GenerativeModel("gemini-2.5-flash")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
os.makedirs("uploads", exist_ok=True)

class QueryModel(BaseModel):
    doc_id:str
    question:str

@app.get("/")
def home():
    return {"message":"Backend is running"}


# func1: upload pdf
@app.post("/upload_pdf")
async def load_pdf(file:UploadFile=File(...)):
    try: 
        extracted_text=""
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                text= page.extract_text()
                if text:
                    extracted_text+=text+"\n"
        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No extraction text is found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
    #clean text 
    lines = extracted_text.split("\n")
    cleaned_lines=[]
    for line in lines:
        line=line.strip()
        if len(line)<20:continue
        if "et al" in line.lower(): continue
        if re.match(r"^\d+$",line):continue
        cleaned_lines.append(line)
    cleaned_text="\n".join(cleaned_lines)

    #  Chunk  
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=200
        )
    chunks = text_splitter.split_text(cleaned_text)

    #create embeddings 
    chunk_embedding=embedder.encode(
        chunks,
        show_progress_bar=True,
        batch_size=32,
        normalize_embeddings=True)
    d=chunk_embedding.shape[1]

     # build faiss index
    index=faiss.IndexFlatL2(d)
    index.add(np.array(chunk_embedding).astype('float32'))
   
    #save everything
    doc_id=os.path.splitext(file.filename)[0]
    doc_dir=f"uploads/{doc_id}"

    try:
        os.makedirs(doc_dir,exist_ok=True)
    except OSError as error:
        print("Invalid path name")

    try:
        faiss.write_index(index,f"{doc_dir}/index.faiss")
        with open(f"{doc_dir}/chunks.json", "w") as f:
            json.dump(chunks, f)
        print(f"saved to {doc_dir}")
        return {
            "doc_id":doc_id,
            "message":f"successfully processed {file.filename}",
            "nums_chunks":len(chunks)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )    


#func2: ask_ Question
@app.post("/query")
async def ask_question(request:QueryModel):
    #load saved data 
    try: 
        doc_dir=f"uploads/{request.doc_id}"
        index=faiss.read_index(f"{doc_dir}/index.faiss")
        with open(f"{doc_dir}/chunks.json","r") as f:
            chunks=json.load(f)
        print(f"load {len(chunks)} chunks for {request.doc_id}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load data{str(e)}"
        )
    # search the relevant chunk
    q_embedding=embedder.encode([request.question]).astype("float32")
    #get top k chunks
    distance,indices=index.search(q_embedding,k=3)
    #get context
    context = "\n\n".join([chunks[i] for i in indices[0]])
    # generate prompt
    prompt = f"""You are a research assistant. Extract the answer strictly from the context provided. 
    If the information is missing, say 'I cannot find this in the paper.' 
    Do not include journal impact factors or metadata unless asked
Context:
{context}

Question: {request.question}

Answer:"""
    try:
        response=gemini.generate_content(prompt)
        answer=response.text.strip()
        return{
            "question":request.question,
            "answer": answer,
            "context":context[:500]+"...",
            "num_chunks_used":len(indices[0])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer:{str(e)}"
        )


#func3: list all uploaded documents
@app.get("/documents")
def list_doc():
    try:
        doc=[]
        if not os.path.exists("uploads"):
            return {
                "documents":[],
                "count":0
            }
        for d in  os.listdir("uploads"):
            doc_path=os.path.join("uploads",d)
            if os.path.isdir(doc_path):
                doc.append(d)
        return {
        "documents":doc,
         "count": len(doc)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )
if __name__ == "__main__":
    import uvicorn
    
    print("Starting server")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)






