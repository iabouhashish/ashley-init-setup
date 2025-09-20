## 🏗️ System Architecture Overview

### The Big Picture
built like a smart factory with specialized departments:

```
User Question → [Data Collection] → [AI Analysis] → [Knowledge Search] → [Safety Check] → [Personalized Answer]
```

### Core Components

#### 1. **API Gateway** (`main.py`)
- **What it does**: The front door that receives user questions
- **Think of it as**: A receptionist who takes your question and coordinates the response
- **Key features**:
  - Handles both regular chat and real-time streaming responses
  - Manages user authentication
  - Coordinates all other services

#### 2. **AI Agent** (`agent.py`) 
- **What it does**: The "brain" that processes questions and generates answers
- **Think of it as**: A medical researcher who:
  - Analyzes your personal health data
  - Searches medical knowledge
  - Identifies patterns and anomalies
  - Provides personalized recommendations
- **Key features**:
  - 6-step analysis pipeline
  - Safety checks for emergency symptoms
  - Citation tracking for all sources

#### 3. **Memory System** (`firestore_memory.py`)
- **What it does**: Stores and retrieves user data and conversation history
- **Think of it as**: A personal health file cabinet
- **Stores**:
  - Chat history (conversations with ChatBot)
  - Health metrics (heart rate, sleep, steps, etc.)
  - User preferences and settings

#### 4. **Knowledge Base** (`retriever.py`)
- **What it does**: Searches through medical literature and guidelines
- **Think of it as**: A medical library with an AI librarian
- **Features**:
  - Vector search (finds relevant information by meaning, not just keywords)
  - Citation tracking
  - Metadata filtering

#### 5. **Data Models** (`schemas.py`)
- **What it does**: Defines the structure of all data
- **Think of it as**: Forms and templates that ensure data consistency

---

## 🔄 How It Works (Step-by-Step)

### When a User Asks a Question:

1. **Question Reception** 📥
   - User sends: "Why is my heart rate high?"
   - System authenticates the user
   - Extracts user ID and question

2. **Data Gathering** 📊
   - Fetches user's recent health metrics (last 7 days by default)
   - Retrieves conversation history for context
   - Identifies which metrics to analyze (heart rate, sleep, etc.)

3. **Data Analysis** 🔍
   - Calculates statistical patterns (average, standard deviation)
   - Identifies anomalies (unusual readings)
   - Flags potential health concerns

4. **Knowledge Search** 📚
   - Searches medical knowledge base for relevant information
   - Finds research papers, guidelines, and best practices
   - Ranks results by relevance to the user's specific situation

5. **Safety Check** ⚠️
   - Scans for emergency symptoms
   - Identifies potentially dangerous patterns
   - Adds appropriate warnings

6. **Answer Generation** 💬
   - Combines personal data with medical knowledge
   - Creates personalized, cited response
   - Adds appropriate disclaimers

7. **Response Delivery** 📤
   - Sends answer back to user
   - Saves conversation to memory
   - Tracks citations for transparency

---

## 🛠️ Technical Infrastructure

### Cloud Services Used

#### **Azure OpenAI** 🤖
- **Purpose**: Powers the AI analysis and response generation
- **What it provides**:
  - GPT models for understanding and generating text
  - Embedding models for semantic search
- **Cost**: Pay-per-use based on API calls

#### **Google Cloud Firestore** 🗄️
- **Purpose**: Stores user data and conversation history
- **What it stores**:
  - User health metrics
  - Chat conversations
  - User preferences
- **Cost**: Based on data storage and read/write operations

#### **Qdrant Vector Database** 🔍
- **Purpose**: Stores and searches medical knowledge
- **What it does**:
  - Converts text to numerical vectors for semantic search
  - Finds relevant medical information by meaning
- **Cost**: Self-hosted (free) or cloud-hosted options

### Development Environment

#### **Docker** 🐳
- **Purpose**: Packages the entire application for easy deployment
- **Benefits**:
  - Consistent environment across different machines
  - Easy to scale and deploy
  - Isolates dependencies

#### **FastAPI** ⚡
- **Purpose**: Web framework for the API
- **Benefits**:
  - High performance
  - Automatic API documentation
  - Built-in validation

---

## 📊 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                USER INTERFACE                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Web App       │  │   Mobile App    │  │   API Client    │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │ HTTPS/REST API
┌─────────────────────▼───────────────────────────────────────────────────────────┐
│                              API GATEWAY                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Server                                      │    │
│  │  • Authentication & Authorization                                      │    │
│  │  • Request Validation                                                  │    │
│  │  • CORS Handling                                                       │    │
│  │  • Rate Limiting                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────────────────────┐
│                              AI AGENT CORE                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │  Parse Question │  │  Pull Metrics   │  │  Analyze Data   │                │
│  └─────────┬───────┘  └─────────┬───────┘  └─────────┬───────┘                │
│            │                    │                    │                        │
│  ┌─────────▼───────┐  ┌─────────▼───────┐  ┌─────────▼───────┐                │
│  │  Retrieve      │  │  Safety Check   │  │  Generate       │                │
│  │  Knowledge     │  │                 │  │  Answer         │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────────────────────┐
│                              DATA LAYER                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Firestore     │  │     Qdrant      │  │  Azure OpenAI   │                │
│  │   (Memory)      │  │ (Knowledge)     │  │   (AI Models)   │                │
│  │                 │  │                 │  │                 │                │
│  │ • User Data     │  │ • Medical Docs  │  │ • GPT Models    │                │
│  │ • Chat History  │  │ • Guidelines    │  │ • Embeddings    │                │
│  │ • Health Metrics│  │ • Research      │  │ • Text Analysis │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Data Flow Diagram

```
User Question
    ↓
[API Gateway] → Authentication & Request Processing
    ↓
[AI Agent] → Question Analysis
    ↓
[Memory System] → Fetch User Data & History
    ↓
[AI Agent] → Statistical Analysis
    ↓
[Knowledge Base] → Search Medical Literature
    ↓
[AI Agent] → Safety Check
    ↓
[AI Agent] → Generate Personalized Answer
    ↓
[Memory System] → Save Conversation
    ↓
[API Gateway] → Return Response to User
```

---

## 🔧 Configuration & Setup

### Environment Variables Required

#### **Azure OpenAI Settings**
- `AZURE_OPENAI_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_API_VERSION`: API version (e.g., "2024-02-15-preview")
- `AZURE_DEPLOYMENT_NAME`: Name of your GPT model deployment
- `AZURE_EMBEDDING_DEPLOYMENT`: Name of your embedding model deployment

#### **Google Cloud Settings**
- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `FIRESTORE_EMULATOR_HOST`: For local development (optional)

#### **Qdrant Settings**
- `QDRANT_HOST`: Qdrant server address (default: "127.0.0.1")
- `QDRANT_PORT`: Qdrant port (default: 6333)
- `QDRANT_COLLECTION`: Collection name for medical knowledge

#### **Application Settings**
- `API_KEY`: Static API key for authentication
- `CORS_ORIGINS`: Allowed frontend domains
- `MAX_CONTEXT_MESSAGES`: Number of previous messages to remember

---

## 🚀 Deployment Options

### 1. **Local Development**
- Uses Docker Compose
- Includes Qdrant vector database
- Uses Firestore emulator
- Perfect for testing and development

### 2. **Cloud Deployment**
- Deploy to cloud platforms (AWS, Azure, GCP)
- Use managed services for databases
- Scale based on usage
- Production-ready setup

### 3. **Hybrid Approach**
- Local development with cloud services
- Best of both worlds
- Cost-effective for development

---

## 💰 Cost Considerations

### **Azure OpenAI**
- **GPT Models**: ~$0.01-0.06 per 1K tokens
- **Embedding Models**: ~$0.0001 per 1K tokens
- **Estimated monthly cost**: $50-500 depending on usage

### **Google Cloud Firestore**
- **Storage**: $0.18 per GB per month
- **Reads**: $0.06 per 100K operations
- **Writes**: $0.18 per 100K operations
- **Estimated monthly cost**: $10-100 depending on users

### **Qdrant**
- **Self-hosted**: Free (server costs only)
- **Cloud-hosted**: $50-500 per month depending on size

### **Total Estimated Monthly Cost**
- **Small scale** (100 users): $100-200
- **Medium scale** (1,000 users): $300-800
- **Large scale** (10,000+ users): $1,000-5,000

---

## 🔒 Security & Privacy

### **Data Protection**
- All user data encrypted in transit and at rest
- API key authentication
- CORS protection for web requests
- No sensitive data in logs

### **Privacy Features**
- User data isolated by user ID
- Conversation history stored securely
- Medical knowledge base is read-only
- No data sharing between users

### **Compliance Considerations**
- HIPAA compliance may be required for health data
- GDPR compliance for EU users
- Data retention policies
- User consent management

---

## 📈 Scalability & Performance

### **Current Capacity**
- **Concurrent users**: 100-1,000 (depending on server specs)
- **Response time**: 2-5 seconds per question
- **Data storage**: Unlimited (Firestore scales automatically)
- **Knowledge base**: 1M+ documents searchable

### **Scaling Options**
- **Horizontal scaling**: Add more API servers
- **Database scaling**: Firestore auto-scales
- **Caching**: Add Redis for frequently accessed data
- **CDN**: Use CloudFlare for static content

---

## 🐛 Monitoring & Maintenance

### **Health Checks**
- `/healthz`: Basic system health
- `/v1/ready`: Detailed readiness check
- Database connectivity tests
- External service availability

### **Logging**
- Request/response logging
- Error tracking
- Performance metrics
- User activity (anonymized)

### **Maintenance Tasks**
- Regular security updates
- Database optimization
- Knowledge base updates
- Performance monitoring

---

## 🎯 Business Value Proposition

### **For Users**
- **Personalized insights**: Answers based on their specific health data
- **Evidence-based**: All recommendations backed by medical literature
- **24/7 availability**: Always available for health questions
- **Privacy-focused**: Data stays secure and private

### **For Healthcare Providers**
- **Reduced workload**: Handles routine health questions
- **Better patient engagement**: Patients get immediate answers
- **Data insights**: Patterns in patient questions and concerns
- **Integration ready**: Can be integrated into existing systems

### **For Organizations**
- **Cost reduction**: Reduces need for human health advisors
- **Scalability**: Can handle thousands of users simultaneously
- **Customization**: Can be tailored to specific health domains
- **Compliance**: Built with healthcare regulations in mind

---

## 🚦 Getting Started Checklist

### **For Development Team**
- [ ] Set up Azure OpenAI account and get API keys
- [ ] Create Google Cloud project and enable Firestore
- [ ] Install Docker and Docker Compose
- [ ] Clone the repository
- [ ] Create `.env` file with all required variables
- [ ] Run `docker-compose up` to start local development
- [ ] Test the API endpoints
- [ ] Load sample medical knowledge into Qdrant

### **For Product Team**
- [ ] Define target user personas
- [ ] Identify key health metrics to track
- [ ] Plan knowledge base content strategy
- [ ] Design user experience flow
- [ ] Set up analytics and monitoring
- [ ] Plan go-to-market strategy

### **For Operations Team**
- [ ] Set up production cloud infrastructure
- [ ] Configure monitoring and alerting
- [ ] Implement backup and disaster recovery
- [ ] Set up CI/CD pipeline
- [ ] Plan maintenance schedule
- [ ] Train support team

---

## 📞 Support & Resources

### **Technical Documentation**
- **API documentation**: Available at `/docs` when running (interactive Swagger UI)
- **OpenAPI specification**: Complete API specification in `swagger.yaml`
- **Code comments**: Extensive inline documentation
- **Architecture diagrams**: Included in this guide

### **API Documentation**
The complete API specification is available in `swagger.yaml` which includes:
- **Interactive documentation**: Test API endpoints directly in your browser
- **Request/response examples**: Real-world examples for all endpoints
- **Authentication details**: How to authenticate API requests
- **Error handling**: Complete error response documentation
- **Data models**: Detailed schemas for all data structures

To view the interactive documentation:
1. Start the application: `docker-compose up`
2. Open your browser to: `http://localhost:8088/docs`
3. Use the "Try it out" buttons to test endpoints

### **Product Manager Configuration**
Ashley includes special endpoints for product managers to adjust system behavior:

#### **Metric Configuration** (`/v1/config/metrics`)
- **GET**: View current metric configuration
- **POST**: Update which health metrics are analyzed

**Example: Adding new metrics**
```bash
# View current configuration
curl -X GET "http://localhost:8088/v1/config/metrics" \
  -H "X-API-Key: your-api-key"

# Add weight and blood pressure to default metrics
curl -X POST "http://localhost:8088/v1/config/metrics" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "default_metric_kinds": ["hr", "hrv", "steps", "sleep", "weight", "blood_pressure"]
  }'
```

**Available Metrics:**
- `hr` - Heart Rate
- `hrv` - Heart Rate Variability  
- `steps` - Step Count
- `sleep` - Sleep Duration
- `weight` - Body Weight
- `blood_pressure` - Blood Pressure
- `temperature` - Body Temperature
- `glucose` - Blood Glucose
- `oxygen_saturation` - Blood Oxygen Level

### **Common Issues**
- **Authentication errors**: Check API keys and endpoints
- **Database connection**: Verify Firestore and Qdrant settings
- **Slow responses**: Check Azure OpenAI quotas and limits
- **Memory issues**: Monitor conversation history limits

### **Getting Help**
- Check logs for error messages
- Verify all environment variables are set
- Test individual components separately
- Contact development team for complex issues

---

## 🔮 Future Enhancements

### **Planned Features**
- **Multi-language support**: Support for different languages
- **Voice interface**: Speech-to-text and text-to-speech
- **Mobile app**: Native mobile application
- **Integration APIs**: Connect with fitness trackers and health apps
- **Advanced analytics**: Deeper insights and trend analysis

### **Potential Integrations**
- **Electronic Health Records (EHR)**: Connect with hospital systems
- **Wearable devices**: Direct integration with fitness trackers
- **Telemedicine platforms**: Integration with video consultation tools
- **Pharmacy systems**: Medication interaction checking

---