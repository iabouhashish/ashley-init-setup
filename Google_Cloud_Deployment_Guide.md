# Ashley AI Health Assistant - Google Cloud Deployment Guide

## 🎯 Overview

This guide provides step-by-step instructions for deploying the Ashley AI Health Assistant as an **additive service** to your existing Google Cloud Platform (GCP) application. The deployment uses Google Cloud Run for the API service and integrates with your existing Firestore database.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING GCP APPLICATION                    │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Main App      │  │   Firestore     │  │   Other         │ │
│  │   (Existing)    │  │   (Existing)    │  │   Services      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                   │                   │            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Ashley        │  │   Cloud Run     │  │  Cloud Storage  │ │
│  │   Chat Bot      │  │   (New)         │  │  (Qdrant Data)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                   │                   │            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Cloud Build   │  │   Secret        │  │   Cloud Logging │ │
│  │   (CI/CD)       │  │   Manager       │  │   (Monitoring)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────────────┐
                    │   Azure OpenAI  │
                    │   (External)    │
                    └─────────────────┘
```

## 📋 Prerequisites

### Required Accounts & Services
- [ ] **Existing GCP project** with Firestore database already running
- [ ] Azure OpenAI account with API access
- [ ] Docker installed locally
- [ ] Google Cloud SDK (gcloud) installed
- [ ] Git repository access

### Required Permissions
- [ ] Cloud Run Admin
- [ ] Cloud Build Editor
- [ ] Secret Manager Admin
- [ ] **Firestore User** (read/write access to existing database)
- [ ] Cloud Storage Admin
- [ ] Cloud Logging Admin

### Existing Infrastructure Assumptions
- [ ] **Firestore database** is already set up and running
- [ ] **GCP project** is already configured
- [ ] **Service accounts** may already exist
- [ ] **Networking** and security policies are in place

## 🚀 Step-by-Step Deployment

### Step 1: Connect to Existing GCP Project

#### 1.1 Set Up Project Access
```bash
# Set your existing project ID
export PROJECT_ID="your-existing-project-id"
export REGION="us-central1"

# Set the project as default
gcloud config set project $PROJECT_ID

# Verify you have access to the existing project
gcloud projects describe $PROJECT_ID
```

#### 1.2 Enable Required APIs (if not already enabled)
```bash
# Enable required Google Cloud APIs for Ashley
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com

# Note: firestore.googleapis.com should already be enabled for your existing app
```

### Step 2: Configure Authentication

#### 2.1 Set up Application Default Credentials
```bash
# Authenticate with Google Cloud
gcloud auth login

# Set up application default credentials
gcloud auth application-default login

# Set default region
gcloud config set run/region $REGION
```

#### 2.2 Create Service Account
```bash
# Create service account for the application
gcloud iam service-accounts create ashley-app-sa \
    --display-name="Ashley Application Service Account" \
    --description="Service account for Ashley AI Health Assistant"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/firestore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 3: Configure Firestore Integration

#### 3.1 Verify Existing Firestore Database
```bash
# Verify your existing Firestore database
gcloud firestore databases list

# Check if you have the right permissions
gcloud firestore collections list
```

#### 3.2 Update Firestore Security Rules (if needed)
If you need to add Ashley-specific collections to your existing Firestore rules, create `ashley-firestore.rules`:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Existing rules for your main app...
    
    // Ashley-specific collections
    match /conversations/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      match /messages/{messageId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      
      match /metrics/{metricId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
}
```

Deploy the updated rules:
```bash
# Deploy updated Firestore security rules
gcloud firestore rules deploy ashley-firestore.rules
```

**Note**: If your existing app already has user-based security rules, Ashley will work with your existing structure. The collections will be created automatically when users start using the chat bot.

### Step 4: Set up Cloud Storage for Qdrant

#### 4.1 Create Storage Bucket for Ashley
```bash
# Create a storage bucket specifically for Ashley's Qdrant data
gsutil mb gs://$PROJECT_ID-ashley-qdrant-data

# Set appropriate permissions for Ashley service account
gsutil iam ch serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://$PROJECT_ID-ashley-qdrant-data
```

**Note**: This creates a separate bucket for Ashley's vector database data, keeping it isolated from your main application's storage.

## 🔗 Integration Considerations

### Data Isolation
- **Firestore Collections**: Ashley uses `/conversations/{userId}/messages` and `/conversations/{userId}/metrics` collections
- **No Conflicts**: These collections won't interfere with your existing app's data structure
- **User Isolation**: Each user's chat data is isolated by `user_id`

### Service Integration
- **Independent Service**: Ashley runs as a separate Cloud Run service
- **API Gateway**: Can be integrated through your existing API gateway or load balancer
- **Authentication**: Uses its own API key system (can be integrated with your existing auth)

### Resource Sharing
- **Firestore**: Shares the same database instance as your main app
- **Logging**: Uses the same Cloud Logging service
- **Monitoring**: Can be integrated with your existing monitoring dashboards

### Step 5: Store Secrets

#### 5.1 Create Secrets in Secret Manager
```bash
# Store Azure OpenAI credentials
echo -n "your-azure-openai-key" | gcloud secrets create azure-openai-key --data-file=-
echo -n "your-azure-openai-endpoint" | gcloud secrets create azure-openai-endpoint --data-file=-
echo -n "your-azure-deployment-name" | gcloud secrets create azure-deployment-name --data-file=-
echo -n "your-azure-embedding-deployment" | gcloud secrets create azure-embedding-deployment --data-file=-
echo -n "your-api-key" | gcloud secrets create api-key --data-file=-

# Grant access to the service account
gcloud secrets add-iam-policy-binding azure-openai-key \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding azure-openai-endpoint \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding azure-deployment-name \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding azure-embedding-deployment \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding api-key \
    --member="serviceAccount:ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 6: Create Production Dockerfile

#### 6.1 Create `Dockerfile.prod`
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY firebase.json .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

### Step 7: Create Cloud Run Configuration

#### 7.1 Create `cloud-run.yaml`
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ashley-api
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/cpu-throttling: "false"
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "1"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/PROJECT_ID/ashley-api:latest
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: "PROJECT_ID"
        - name: QDRANT_HOST
          value: "qdrant"
        - name: QDRANT_PORT
          value: "6333"
        - name: QDRANT_COLLECTION
          value: "memory"
        - name: QDRANT_DISTANCE
          value: "COSINE"
        - name: EMBEDDING_DIM
          value: "1536"
        - name: FIRESTORE_COLLECTION
          value: "conversations"
        - name: MAX_CONTEXT_MESSAGES
          value: "12"
        - name: DEFAULT_METRIC_KINDS
          value: "hr,hrv,steps,sleep"
        - name: AVAILABLE_METRIC_KINDS
          value: "hr,hrv,steps,sleep,weight,blood_pressure,temperature,glucose,oxygen_saturation"
        - name: CORS_ORIGINS
          value: "*"
        - name: AZURE_OPENAI_KEY
          valueFrom:
            secretKeyRef:
              name: azure-openai-key
              key: latest
        - name: AZURE_OPENAI_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: azure-openai-endpoint
              key: latest
        - name: AZURE_DEPLOYMENT_NAME
          valueFrom:
            secretKeyRef:
              name: azure-deployment-name
              key: latest
        - name: AZURE_EMBEDDING_DEPLOYMENT
          valueFrom:
            secretKeyRef:
              name: azure-embedding-deployment
              key: latest
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-key
              key: latest
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "1"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Step 8: Deploy Qdrant as a Sidecar

#### 8.1 Create `qdrant-deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
  labels:
    app: qdrant
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        - containerPort: 6334
        env:
        - name: QDRANT__SERVICE__HTTP_PORT
          value: "6333"
        - name: QDRANT__SERVICE__GRPC_PORT
          value: "6334"
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"
          requests:
            cpu: "0.5"
            memory: "1Gi"
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
      volumes:
      - name: qdrant-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
spec:
  selector:
    app: qdrant
  ports:
  - port: 6333
    targetPort: 6333
  - port: 6334
    targetPort: 6334
  type: ClusterIP
```

### Step 9: Set up CI/CD Pipeline

#### 9.1 Create `cloudbuild.yaml`
```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ashley-api:$COMMIT_SHA', '-f', 'Dockerfile.prod', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ashley-api:$COMMIT_SHA']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'run'
    - 'deploy'
    - 'ashley-api'
    - '--image'
    - 'gcr.io/$PROJECT_ID/ashley-api:$COMMIT_SHA'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--service-account'
    - 'ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com'
    - '--memory'
    - '4Gi'
    - '--cpu'
    - '2'
    - '--max-instances'
    - '10'
    - '--min-instances'
    - '1'
    - '--timeout'
    - '300'
    - '--concurrency'
    - '100'

  # Deploy Qdrant
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'kubectl'
    - 'apply'
    - '-f'
    - 'qdrant-deployment.yaml'

images:
  - 'gcr.io/$PROJECT_ID/ashley-api:$COMMIT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'
```

#### 9.2 Create GitHub Actions Workflow (`.github/workflows/deploy.yml`)
```yaml
name: Deploy to Google Cloud

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Configure Docker
      run: gcloud auth configure-docker
    
    - name: Build and Push
      run: |
        docker build -t gcr.io/$PROJECT_ID/ashley-api:$GITHUB_SHA -f Dockerfile.prod .
        docker push gcr.io/$PROJECT_ID/ashley-api:$GITHUB_SHA
    
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy ashley-api \
          --image gcr.io/$PROJECT_ID/ashley-api:$GITHUB_SHA \
          --region $REGION \
          --platform managed \
          --allow-unauthenticated \
          --service-account ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com \
          --memory 4Gi \
          --cpu 2 \
          --max-instances 10 \
          --min-instances 1 \
          --timeout 300 \
          --concurrency 100
```

### Step 10: Deploy Ashley as Additional Service

#### 10.1 Build and Deploy Ashley
```bash
# Build the Ashley container image
docker build -t gcr.io/$PROJECT_ID/ashley-api:latest -f Dockerfile.prod .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/ashley-api:latest

# Deploy Ashley as a new Cloud Run service (alongside your existing services)
gcloud run deploy ashley-api \
  --image gcr.io/$PROJECT_ID/ashley-api:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --service-account ashley-app-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --memory 4Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 1 \
  --timeout 300 \
  --concurrency 100
```

#### 10.2 Integration with Existing Infrastructure
```bash
# Get the Ashley service URL
export ASHLEY_URL=$(gcloud run services describe ashley-api --region $REGION --format="value(status.url)")

# Test the integration
curl -X GET "$ASHLEY_URL/healthz"

# Your main app can now call Ashley at: $ASHLEY_URL/v1/chat
```

#### 10.3 Deploy Qdrant (Optional)
```bash
# Deploy Qdrant to GKE (if using GKE)
gcloud container clusters create ashley-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type e2-medium

# Get cluster credentials
gcloud container clusters get-credentials ashley-cluster --zone us-central1-a

# Deploy Qdrant
kubectl apply -f qdrant-deployment.yaml
```

### Step 11: Set up Monitoring and Logging

#### 11.1 Create Monitoring Dashboard
```bash
# Create monitoring dashboard
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

#### 11.2 Create `dashboard.json`
```json
{
  "displayName": "Ashley API Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"ashley-api\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["metric.labels.response_code"]
                    }
                  }
                }
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Response Time",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"ashley-api\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_MEAN"
                    }
                  }
                }
              }
            ]
          }
        }
      }
    ]
  }
}
```

### Step 12: Set up Custom Domain (Optional)

#### 12.1 Configure Custom Domain
```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
  --service ashley-api \
  --domain api.ashley-health.com \
  --region $REGION
```

#### 12.2 SSL Certificate
```bash
# Create SSL certificate
gcloud compute ssl-certificates create ashley-ssl-cert \
  --domains=api.ashley-health.com \
  --global
```

## 🔌 Integration with Your Existing App

### Frontend Integration
```javascript
// Example: Add Ashley chat to your existing frontend
const ASHLEY_API_URL = 'https://ashley-api-xxxxx-uc.a.run.app/v1';

// Chat with Ashley
async function chatWithAshley(userId, message) {
  const response = await fetch(`${ASHLEY_API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({
      user_id: userId,
      message: message,
      metric_kinds: ['hr', 'hrv', 'steps', 'sleep'] // Optional
    })
  });
  
  return await response.json();
}

// Stream chat with Ashley
async function streamChatWithAshley(userId, message) {
  const response = await fetch(`${ASHLEY_API_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({
      user_id: userId,
      message: message
    })
  });
  
  // Handle Server-Sent Events
  const reader = response.body.getReader();
  // ... handle streaming response
}
```

### Backend Integration
```python
# Example: Add Ashley to your existing backend
import requests

ASHLEY_API_URL = "https://ashley-api-xxxxx-uc.a.run.app/v1"
ASHLEY_API_KEY = "your-api-key"

def get_health_insights(user_id, question):
    """Get health insights from Ashley"""
    response = requests.post(
        f"{ASHLEY_API_URL}/chat",
        headers={"X-API-Key": ASHLEY_API_KEY},
        json={
            "user_id": user_id,
            "message": question,
            "metric_kinds": ["hr", "hrv", "steps", "sleep"]
        }
    )
    return response.json()

# Use in your existing endpoints
@app.route('/api/health-chat', methods=['POST'])
def health_chat():
    user_id = request.json.get('user_id')
    message = request.json.get('message')
    
    # Get response from Ashley
    ashley_response = get_health_insights(user_id, message)
    
    return jsonify({
        "reply": ashley_response["reply"],
        "sources": ashley_response.get("used_docs", [])
    })
```

### Data Flow Integration
```
Your App Frontend → Your App Backend → Ashley API → Firestore (shared)
                                    ↓
                              Azure OpenAI
                                    ↓
                              Qdrant (Ashley's knowledge)
```

## 🔧 Configuration Management

### Environment Variables
All sensitive configuration is stored in Google Secret Manager:

| Secret Name | Description | Usage |
|-------------|-------------|-------|
| `azure-openai-key` | Azure OpenAI API key | AI model access |
| `azure-openai-endpoint` | Azure OpenAI endpoint URL | AI model access |
| `azure-deployment-name` | GPT model deployment name | AI model access |
| `azure-embedding-deployment` | Embedding model deployment | Vector search |
| `api-key` | Application API key | Authentication |

### Non-Sensitive Configuration
Stored as environment variables in Cloud Run:

| Variable | Value | Description |
|----------|-------|-------------|
| `GCP_PROJECT_ID` | `ashley-health-prod` | GCP project ID |
| `QDRANT_HOST` | `qdrant` | Qdrant service name |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `memory` | Vector collection name |
| `FIRESTORE_COLLECTION` | `conversations` | Firestore collection |
| `MAX_CONTEXT_MESSAGES` | `12` | Chat history limit |
| `DEFAULT_METRIC_KINDS` | `hr,hrv,steps,sleep` | Default metrics to analyze |
| `AVAILABLE_METRIC_KINDS` | `hr,hrv,steps,sleep,weight,blood_pressure,temperature,glucose,oxygen_saturation` | All available metrics |

## 📊 Monitoring and Alerting

### Key Metrics to Monitor
- **Request Rate**: Requests per second
- **Response Time**: Average response time
- **Error Rate**: 4xx and 5xx error percentage
- **Memory Usage**: Container memory consumption
- **CPU Usage**: Container CPU utilization
- **Cold Starts**: Service startup frequency

### Alerting Rules
```bash
# Create alerting policy for high error rate
gcloud alpha monitoring policies create --policy-from-file=error-rate-policy.yaml

# Create alerting policy for high response time
gcloud alpha monitoring policies create --policy-from-file=response-time-policy.yaml
```

## 🔒 Security Considerations

### Network Security
- Cloud Run services are protected by Google's infrastructure
- Firestore uses encrypted connections
- All secrets are encrypted at rest

### Access Control
- Service accounts with minimal required permissions
- Firestore security rules for data isolation
- API key authentication for external access

### Data Protection
- All data encrypted in transit and at rest
- User data isolated by user ID
- No cross-user data access

## 💰 Cost Optimization

### Estimated Monthly Costs
- **Cloud Run**: $50-200 (depending on traffic)
- **Firestore**: $20-100 (depending on data)
- **Cloud Storage**: $5-20 (Qdrant data)
- **Secret Manager**: $5-10
- **Monitoring**: $10-30
- **Total**: $90-360/month

### Cost Optimization Tips
1. **Right-size instances**: Start with 1 CPU, 2GB RAM
2. **Use preemptible instances**: For non-critical workloads
3. **Set up billing alerts**: Monitor spending
4. **Optimize Firestore queries**: Use indexes efficiently
5. **Implement caching**: Reduce API calls

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
gcloud run services logs read ashley-api --region $REGION

# Check service status
gcloud run services describe ashley-api --region $REGION
```

#### 2. Database Connection Issues
```bash
# Test Firestore connection
gcloud firestore databases list

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID
```

#### 3. Secret Access Issues
```bash
# Verify secret exists
gcloud secrets list

# Test secret access
gcloud secrets versions access latest --secret="azure-openai-key"
```

### Debug Commands
```bash
# Get service URL
gcloud run services describe ashley-api --region $REGION --format="value(status.url)"

# Test health endpoint
curl https://YOUR_SERVICE_URL/healthz

# Check service logs
gcloud run services logs tail ashley-api --region $REGION
```

## 🔄 Updates and Maintenance

### Rolling Updates
```bash
# Deploy new version
gcloud run deploy ashley-api --image gcr.io/$PROJECT_ID/ashley-api:new-version

# Rollback if needed
gcloud run services update-traffic ashley-api --to-revisions=REVISION_NAME=100
```

### Database Migrations
```bash
# Backup Firestore data
gcloud firestore export gs://$PROJECT_ID-backups/firestore-backup

# Restore from backup
gcloud firestore import gs://$PROJECT_ID-backups/firestore-backup
```

## 📈 Scaling

### Automatic Scaling
- Cloud Run automatically scales based on traffic
- Configure min/max instances based on expected load
- Set appropriate concurrency limits

### Manual Scaling
```bash
# Scale up for high traffic
gcloud run services update ashley-api --region $REGION --min-instances 5 --max-instances 20

# Scale down for low traffic
gcloud run services update ashley-api --region $REGION --min-instances 1 --max-instances 5
```

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] GCP project created and billing enabled
- [ ] Required APIs enabled
- [ ] Service account created with proper permissions
- [ ] Secrets stored in Secret Manager
- [ ] Firestore database created
- [ ] Cloud Storage bucket created

### Deployment
- [ ] Container image built and pushed
- [ ] Cloud Run service deployed
- [ ] Qdrant deployed (if using GKE)
- [ ] Custom domain configured (if needed)
- [ ] SSL certificate installed (if using custom domain)

### Post-Deployment
- [ ] Health checks passing
- [ ] API endpoints responding correctly
- [ ] Monitoring dashboard configured
- [ ] Alerting rules set up
- [ ] Documentation updated with production URLs
- [ ] Team trained on deployment process

## 🆘 Support and Resources

### Google Cloud Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)

### Troubleshooting Resources
- [Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
- [Firestore Troubleshooting](https://cloud.google.com/firestore/docs/troubleshooting)
- [Google Cloud Support](https://cloud.google.com/support)

---

*This deployment guide provides comprehensive instructions for deploying Ashley to Google Cloud Platform. For additional support or questions, refer to the Google Cloud documentation or contact the development team.*
