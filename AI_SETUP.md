# AI Configuration Guide

## Setting Up Real AI (OpenAI GPT-4)

Your ARGO platform now supports **real AI** powered by OpenAI's GPT-4 model. Here's how to enable it:

### Option 1: Use OpenAI GPT-4 (Recommended)

1. **Get an OpenAI API Key**:
   - Go to https://platform.openai.com/api-keys
   - Sign up or log in
   - Create a new API key
   - Copy the key (starts with `sk-...`)

2. **Add API Key to Backend**:
   
   Edit `backend/.env`:
   ```bash
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. **Restart Backend**:
   ```bash
   cd backend
   python main.py
   ```

4. **That's it!** The AI will now use GPT-4 for intelligent responses.

### What You Get with GPT-4

✅ **Advanced Reasoning**: Deep oceanographic analysis  
✅ **Context Understanding**: Interprets complex scientific queries  
✅ **Intelligent Visualizations**: Automatically suggests appropriate graph types  
✅ **Scientific Explanations**: Detailed, accurate oceanographic insights  
✅ **Conversational**: Natural, helpful responses  

### Current Fallback System

Without an OpenAI API key, the system uses an **intelligent fallback** that:
- Extracts statistics from retrieved data
- Provides summary analysis
- Suggests appropriate visualizations
- References specific data points

It's functional but not as sophisticated as GPT-4.

## AI Capabilities

### Visualization Intelligence

The AI can recommend and generate:

1. **Histograms**: Distribution analysis
   - Temperature distribution
   - Salinity distribution
   - Depth distribution

2. **Scatter Plots**: Correlation analysis
   - Temperature vs Salinity
   - Custom variable relationships
   - Shows correlation coefficient

3. **Depth Profiles**: Vertical ocean structure
   - Temperature vs Depth
   - Salinity vs Depth
   - Pressure profiles

4. **Heatmaps**: Spatial patterns
   - Geographic temperature distribution
   - Salinity maps
   - Density plots

5. **3D Scatter**: Multi-variable relationships
   - Temperature-Salinity-Depth relationships
   - 3D ocean property space

6. **Time Series**: Temporal trends
   - Sequential measurements
   - Trend analysis

7. **Correlation Matrix**: Variable relationships
   - All-variable correlations
   - Statistical insights

### Example Queries

Try asking:

- "Show me the temperature distribution"
- "What's the correlation between temperature and salinity?"
- "Generate a depth profile for temperature"
- "Create a heatmap of ocean temperatures"
- "Show me a 3D scatter plot of temperature, salinity, and depth"
- "What are the temperature patterns in the Arctic data?"
- "Explain why salinity varies with depth"
- "Show me a scatter plot to see the relationship between variables"

The AI will:
1. Understand your query using RAG (Retrieval-Augmented Generation)
2. Retrieve relevant data from the database
3. Analyze the data with GPT-4
4. Suggest appropriate visualizations
5. Generate interactive graphs automatically

## Cost Considerations

### OpenAI Pricing (as of 2024)

- GPT-4 Turbo: $0.01 per 1K input tokens, $0.03 per 1K output tokens
- Typical query: ~$0.01-0.05
- For research use, costs are minimal

### Free Alternative

If you don't want to use OpenAI, the fallback system is completely free and works well for basic analysis.

## Troubleshooting

### "Using fallback response generation"

This message means no OpenAI API key is configured. The system will still work but with reduced AI capabilities.

### "OpenAI API error"

Check:
1. API key is correct in `.env`
2. You have API credits in your OpenAI account
3. Internet connection is working
4. OpenAI service is operational

### Backend won't start

Make sure all packages are installed:
```bash
cd backend
pip install openai>=1.6.1
```

## Advanced: Local AI (Coming Soon)

Want to run AI locally without API costs? We're planning support for:
- Ollama (llama3, mistral)
- LocalAI
- LM Studio

This will let you run AI models on your own hardware with no API costs!

## Questions?

The AI assistant itself can answer questions about how it works. Just ask!
