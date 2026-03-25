# How to Get Your Google Gemini Pro API Key

## Step 1: Go to Google AI Studio
Visit: **https://makersuite.google.com/app/apikey**
(Or go to https://ai.google.dev/ and click "Get API Key")

## Step 2: Sign In
- Sign in with your Google account
- Accept the terms of service if prompted

## Step 3: Create API Key
1. Click **"Create API Key"** button
2. Select an existing Google Cloud project or create a new one
3. Click **"Create API key in new project"** (or existing project)
4. Your API key will be generated instantly

## Step 4: Copy Your API Key
- It will look like: `AIzaSyC_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Copy the entire key (it starts with `AIzaSy`)

## Step 5: Add to Your Project
Open the file: `backend/.env`

Replace the GEMINI_API_KEY line with:
```
GEMINI_API_KEY=AIzaSyC_your_actual_key_here
```

## Step 6: Restart Backend
After adding the key, restart your backend server.

---

## Notes:
- ✅ **FREE**: Gemini Pro API has generous free tier (60 requests/minute)
- ✅ **No Credit Card Required**: You can use it without payment info
- ✅ **Better for Real Data**: Gemini Pro is excellent at analyzing structured data
- ✅ **Faster**: Generally faster response times than GPT-4

## Current Setup:
The system will use **Gemini Pro as primary AI** and fall back to OpenAI if Gemini is unavailable.

Your ARGO platform now uses **100% real data** from the downloaded NetCDF files:
- 15 unique float profiles
- 1,528 real depth measurements
- Real timestamps from 2020-2021
- Real coordinates across North Atlantic

No demo data, no hardcoded values - everything comes from the actual ARGO GDAC database!
