# Qdrant Data Management Guide for Ashley

## 🎯 Overview

This guide explains how to add, manage, and maintain data in Qdrant for the Ashley AI Health Assistant. Qdrant stores the medical knowledge base that Ashley uses to provide informed health responses.

## 🏗️ How Qdrant Works in Ashley

### Data Flow
```
Medical Documents → Text Processing → Vector Embeddings → Qdrant Storage
                                                           ↓
User Questions → Vector Search → Similar Documents → AI Response
```

### Data Structure
Each document in Qdrant contains:
- **Vector**: 1536-dimensional embedding (from Azure OpenAI)
- **Text**: The actual document content
- **Metadata**: Additional information (source, category, etc.)

## 📊 Data Types and Sources

### **Medical Knowledge Sources**
- **Research Papers**: Academic studies and clinical research
- **Medical Guidelines**: Official health organization recommendations
- **Drug Information**: Medication details and interactions
- **Symptom Databases**: Common symptoms and their meanings
- **Treatment Protocols**: Standard medical procedures
- **Health Articles**: Educational content from trusted sources

### **Data Categories**
- `cardiovascular` - Heart and blood vessel health
- `respiratory` - Lung and breathing health
- `neurological` - Brain and nervous system
- `metabolic` - Diabetes, thyroid, metabolism
- `mental_health` - Psychology and psychiatry
- `preventive` - Wellness and prevention
- `emergency` - Urgent care and emergency procedures

## 🚀 Methods to Add Data

### **Method 1: Using the API (Recommended for Production)**

#### **Single Document Upload**
```bash
curl -X POST "https://your-ashley-api.com/v1/index/upsert" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "text": "Heart rate variability (HRV) is a measure of the variation in time between heartbeats. Higher HRV is generally associated with better cardiovascular health and fitness.",
        "metadata": {
          "source": "American Heart Association",
          "title": "Heart Rate Variability Guidelines",
          "category": "cardiovascular",
          "url": "https://www.heart.org/en/health-topics/high-blood-pressure",
          "date": "2024-01-15",
          "author": "AHA Medical Team"
        },
        "id": "hrv_guidelines_001"
      }
    ]
  }'
```

#### **Batch Document Upload**
```bash
curl -X POST "https://your-ashley-api.com/v1/index/upsert" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "text": "Normal resting heart rate for adults ranges from 60 to 100 beats per minute (bpm). Athletes may have resting heart rates as low as 40 bpm.",
        "metadata": {
          "source": "Mayo Clinic",
          "title": "Normal Heart Rate",
          "category": "cardiovascular",
          "url": "https://www.mayoclinic.org/healthy-lifestyle/fitness/expert-answers/heart-rate/faq-20057979"
        }
      },
      {
        "text": "Sleep is essential for physical and mental health. Adults should aim for 7-9 hours of quality sleep per night.",
        "metadata": {
          "source": "Sleep Foundation",
          "title": "Sleep Requirements",
          "category": "preventive",
          "url": "https://www.sleepfoundation.org/how-sleep-works/how-much-sleep-do-we-really-need"
        }
      }
    ]
  }'
```

### **Method 2: Using Python Scripts**

#### **Basic Data Upload Script**
```python
# upload_data.py
import requests
import json

ASHLEY_API_URL = "https://your-ashley-api.com/v1"
API_KEY = "your-api-key"

def upload_document(text, metadata, doc_id=None):
    """Upload a single document to Qdrant via Ashley API"""
    payload = {
        "items": [
            {
                "text": text,
                "metadata": metadata,
                "id": doc_id
            }
        ]
    }
    
    response = requests.post(
        f"{ASHLEY_API_URL}/index/upsert",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✅ Document uploaded successfully: {doc_id or 'auto-generated'}")
        return response.json()
    else:
        print(f"❌ Upload failed: {response.text}")
        return None

# Example usage
document = {
    "text": "Blood pressure is the force of blood pushing against the walls of arteries. Normal blood pressure is less than 120/80 mmHg.",
    "metadata": {
        "source": "American Heart Association",
        "title": "Understanding Blood Pressure",
        "category": "cardiovascular",
        "url": "https://www.heart.org/en/health-topics/high-blood-pressure",
        "date": "2024-01-20"
    },
    "id": "bp_guide_001"
}

result = upload_document(
    text=document["text"],
    metadata=document["metadata"],
    doc_id=document["id"]
)
```

#### **Batch Upload from CSV**
```python
# batch_upload.py
import pandas as pd
import requests
import json
from typing import List, Dict

def upload_from_csv(csv_file: str, api_url: str, api_key: str):
    """Upload documents from CSV file"""
    df = pd.read_csv(csv_file)
    
    # Convert CSV to API format
    items = []
    for _, row in df.iterrows():
        item = {
            "text": row["text"],
            "metadata": {
                "source": row.get("source", "Unknown"),
                "title": row.get("title", ""),
                "category": row.get("category", "general"),
                "url": row.get("url", ""),
                "date": row.get("date", "")
            }
        }
        if "id" in row and pd.notna(row["id"]):
            item["id"] = str(row["id"])
        
        items.append(item)
    
    # Upload in batches of 100
    batch_size = 100
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        payload = {"items": batch}
        
        response = requests.post(
            f"{api_url}/index/upsert",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            print(f"✅ Batch {i//batch_size + 1} uploaded successfully")
        else:
            print(f"❌ Batch {i//batch_size + 1} failed: {response.text}")

# Example CSV format:
# text,source,title,category,url,date,id
# "Heart rate variability...",AHA,HRV Guidelines,cardiovascular,https://...,2024-01-15,hrv_001
# "Sleep is essential...",Sleep Foundation,Sleep Requirements,preventive,https://...,2024-01-16,sleep_001

# Usage
upload_from_csv("medical_documents.csv", ASHLEY_API_URL, API_KEY)
```

### **Method 3: Direct Qdrant Integration (Advanced)**

#### **Direct Qdrant Client Script**
```python
# direct_qdrant_upload.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import AzureOpenAIEmbeddings
import json

# Configuration
QDRANT_HOST = "localhost"  # or your Qdrant host
QDRANT_PORT = 6333
COLLECTION_NAME = "memory"
AZURE_OPENAI_KEY = "your-azure-key"
AZURE_OPENAI_ENDPOINT = "your-azure-endpoint"
AZURE_EMBEDDING_DEPLOYMENT = "your-embedding-deployment"

def setup_qdrant():
    """Initialize Qdrant client and create collection if needed"""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Create collection if it doesn't exist
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        print(f"✅ Created collection: {COLLECTION_NAME}")
    
    return client

def upload_documents_direct(documents: List[Dict]):
    """Upload documents directly to Qdrant"""
    client = setup_qdrant()
    
    # Initialize embedding model
    embedder = AzureOpenAIEmbeddings(
        azure_deployment=AZURE_EMBEDDING_DEPLOYMENT,
        api_key=AZURE_OPENAI_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2024-02-15-preview"
    )
    
    # Prepare documents
    texts = [doc["text"] for doc in documents]
    vectors = embedder.embed_documents(texts)
    
    # Create points
    points = []
    for i, doc in enumerate(documents):
        point = PointStruct(
            id=doc.get("id"),
            vector=vectors[i],
            payload={
                "text": doc["text"],
                **doc.get("metadata", {})
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅ Uploaded {len(documents)} documents to Qdrant")

# Example usage
documents = [
    {
        "id": "doc_001",
        "text": "Exercise is one of the most important things you can do for your health.",
        "metadata": {
            "source": "CDC",
            "title": "Physical Activity Guidelines",
            "category": "preventive"
        }
    }
]

upload_documents_direct(documents)
```

## 📝 Data Format Standards

### **Required Fields**
```json
{
  "text": "The actual content of the document",
  "metadata": {
    "source": "Where the information comes from",
    "title": "Document title",
    "category": "Document category"
  }
}
```

### **Optional Fields**
```json
{
  "id": "unique_document_id",
  "metadata": {
    "url": "https://source-url.com",
    "date": "2024-01-15",
    "author": "Author Name",
    "version": "1.0",
    "language": "en",
    "tags": ["tag1", "tag2"],
    "confidence": 0.95,
    "last_updated": "2024-01-20T10:30:00Z"
  }
}
```

### **Category Guidelines**
- **cardiovascular**: Heart, blood vessels, circulation
- **respiratory**: Lungs, breathing, oxygen
- **neurological**: Brain, nerves, mental health
- **metabolic**: Diabetes, thyroid, metabolism
- **preventive**: Wellness, exercise, nutrition
- **emergency**: Urgent care, first aid
- **medication**: Drugs, treatments, side effects
- **symptoms**: Signs, indicators, conditions

## 🔍 Data Quality Guidelines

### **Text Content**
- ✅ **Clear and concise**: Easy to understand
- ✅ **Factual accuracy**: Verified medical information
- ✅ **Appropriate length**: 50-2000 characters per document
- ✅ **Complete sentences**: Avoid fragments
- ❌ **Avoid**: Personal anecdotes, unverified claims, outdated information

### **Metadata Standards**
- ✅ **Consistent sources**: Use standardized source names
- ✅ **Proper categorization**: Use predefined categories
- ✅ **Valid URLs**: Ensure links work
- ✅ **Date formatting**: Use ISO 8601 format (YYYY-MM-DD)
- ❌ **Avoid**: Inconsistent naming, missing required fields

### **Example High-Quality Document**
```json
{
  "text": "High blood pressure (hypertension) is a common condition where the force of blood against artery walls is consistently too high. Normal blood pressure is less than 120/80 mmHg. Hypertension is defined as 130/80 mmHg or higher. Risk factors include age, family history, obesity, lack of exercise, and high sodium diet. Treatment typically involves lifestyle changes and medication.",
  "metadata": {
    "source": "American Heart Association",
    "title": "Understanding High Blood Pressure",
    "category": "cardiovascular",
    "url": "https://www.heart.org/en/health-topics/high-blood-pressure",
    "date": "2024-01-15",
    "author": "AHA Medical Team",
    "version": "2.1",
    "tags": ["hypertension", "blood pressure", "cardiovascular"],
    "confidence": 0.98
  },
  "id": "hypertension_guide_2024"
}
```

## 🛠️ Data Management Operations

### **Search and Verify Data**
```bash
# Search for documents
curl -X POST "https://your-ashley-api.com/v1/index/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "heart rate variability",
    "k": 5
  }'
```

### **Delete Documents**
```bash
# Delete specific documents
curl -X POST "https://your-ashley-api.com/v1/index/delete" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["doc_001", "doc_002"]
  }'
```

### **Bulk Operations Script**
```python
# bulk_operations.py
import requests
import json

class QdrantManager:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    
    def search_documents(self, query: str, k: int = 5, category: str = None):
        """Search for documents"""
        payload = {"query": query, "k": k}
        if category:
            payload["where"] = {"key": "category", "value": category}
        
        response = requests.post(
            f"{self.api_url}/index/search",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_collection_stats(self):
        """Get basic collection statistics"""
        # This would require direct Qdrant access
        # For now, search with a broad query to estimate size
        results = self.search_documents("health", k=1000)
        return {
            "total_documents": len(results.get("results", [])),
            "categories": set(
                doc["metadata"].get("category", "unknown") 
                for doc in results.get("results", [])
            )
        }
    
    def cleanup_duplicates(self, category: str = None):
        """Find and remove duplicate documents"""
        # This is a simplified example
        # In practice, you'd need more sophisticated duplicate detection
        results = self.search_documents("", k=1000, category=category)
        
        seen_texts = set()
        duplicates = []
        
        for doc in results.get("results", []):
            text = doc["text"]
            if text in seen_texts:
                duplicates.append(doc["metadata"].get("id"))
            else:
                seen_texts.add(text)
        
        if duplicates:
            self.delete_documents(duplicates)
            print(f"✅ Removed {len(duplicates)} duplicate documents")
        else:
            print("✅ No duplicates found")

# Usage
manager = QdrantManager("https://your-ashley-api.com/v1", "your-api-key")
stats = manager.get_collection_stats()
print(f"Collection stats: {stats}")
```

## 📊 Data Sources and Acquisition

### **Free Medical Sources**
1. **PubMed**: Academic research papers
2. **CDC**: Public health guidelines
3. **WHO**: International health standards
4. **Mayo Clinic**: Patient education materials
5. **WebMD**: General health information
6. **MedlinePlus**: NIH health information

### **Premium Sources**
1. **UpToDate**: Clinical decision support
2. **Cochrane Library**: Systematic reviews
3. **BMJ Best Practice**: Evidence-based guidelines
4. **Dynamed**: Point-of-care reference

### **Data Extraction Tools**
```python
# web_scraper.py - Example for extracting data from websites
import requests
from bs4 import BeautifulSoup
import json

def extract_medical_content(url: str, source: str):
    """Extract medical content from a webpage"""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract main content (customize based on website structure)
    content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
    
    if content:
        text = content.get_text(strip=True)
        return {
            "text": text,
            "metadata": {
                "source": source,
                "url": url,
                "extracted_date": "2024-01-20"
            }
        }
    return None

# Usage
content = extract_medical_content(
    "https://www.heart.org/en/health-topics/high-blood-pressure",
    "American Heart Association"
)
if content:
    # Upload to Qdrant
    upload_document(content["text"], content["metadata"])
```

## 🔄 Data Maintenance

### **Regular Maintenance Tasks**
1. **Update outdated information** (monthly)
2. **Remove duplicate documents** (weekly)
3. **Add new medical guidelines** (as available)
4. **Monitor data quality** (continuous)
5. **Backup collection** (daily)

### **Automated Data Pipeline**
```python
# automated_pipeline.py
import schedule
import time
from datetime import datetime

def daily_maintenance():
    """Daily maintenance tasks"""
    print(f"Running daily maintenance at {datetime.now()}")
    
    # Check for new documents to add
    # Update existing documents
    # Monitor system health
    
def weekly_cleanup():
    """Weekly cleanup tasks"""
    print(f"Running weekly cleanup at {datetime.now()}")
    
    # Remove duplicates
    # Archive old documents
    # Update statistics

def monthly_update():
    """Monthly update tasks"""
    print(f"Running monthly update at {datetime.now()}")
    
    # Add new medical guidelines
    # Update existing content
    # Generate reports

# Schedule tasks
schedule.every().day.at("02:00").do(daily_maintenance)
schedule.every().sunday.at("03:00").do(weekly_cleanup)
schedule.every().month.do(monthly_update)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## 📈 Monitoring and Analytics

### **Data Quality Metrics**
- **Document count**: Total documents in collection
- **Category distribution**: Documents per category
- **Source diversity**: Number of unique sources
- **Update frequency**: How often data is refreshed
- **Search performance**: Query response times

### **Health Check Script**
```python
# health_check.py
def check_qdrant_health(api_url: str, api_key: str):
    """Check Qdrant collection health"""
    try:
        # Test search functionality
        response = requests.post(
            f"{api_url}/index/search",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"query": "test", "k": 1}
        )
        
        if response.status_code == 200:
            print("✅ Qdrant search is working")
            return True
        else:
            print(f"❌ Qdrant search failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Qdrant health check failed: {e}")
        return False
```

## 🚀 Best Practices

### **Data Addition**
1. **Start small**: Begin with high-quality, verified sources
2. **Batch uploads**: Use batch operations for efficiency
3. **Validate data**: Check content before uploading
4. **Monitor quality**: Regularly review search results
5. **Version control**: Keep track of data updates

### **Performance Optimization**
1. **Chunk large documents**: Split long texts into smaller pieces
2. **Use appropriate categories**: Enable better filtering
3. **Regular cleanup**: Remove outdated or duplicate content
4. **Monitor usage**: Track which documents are most relevant

### **Security Considerations**
1. **API key protection**: Secure your API keys
2. **Data validation**: Sanitize input data
3. **Access control**: Limit who can modify data
4. **Audit logging**: Track data changes

---

*This guide provides comprehensive instructions for managing data in Qdrant for the Ashley AI Health Assistant. Start with the API methods for simplicity, then explore direct Qdrant integration for advanced use cases.*
