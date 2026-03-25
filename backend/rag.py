"""
RAG (Retrieval-Augmented Generation) Pipeline

This module provides:
1. Vector similarity search using FAISS
2. Context retrieval from database
3. LLM integration (OpenAI or local models)
4. Response generation with retrieved context
"""
import os
import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from models import ArgoDocument, ArgoProfile
from config import settings

# Lazy import for sentence_transformers (may fail if PyTorch version is incompatible)
SentenceTransformer = None
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    print(f"⚠ sentence_transformers not available: {e}")
    print("  RAG will operate in fallback mode without vector search")


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for ARGO data."""
    
    def __init__(self):
        """Initialize RAG pipeline components."""
        print("Initializing RAG pipeline...")
        
        # Load embedding model (may be None if sentence_transformers failed)
        self.model = None
        self.dimension = 384  # default dimension for all-MiniLM-L6-v2
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                self.dimension = self.model.get_sentence_embedding_dimension()
            except Exception as e:
                print(f"⚠ Could not load embedding model: {e}")
        
        # Load FAISS index
        self.index = None
        self.vector_id_mapping = None
        self._load_index()
        
        # Initialize LLM (OpenAI or fallback)
        self._init_llm()
        
        print("✓ RAG pipeline initialized")
    
    def _load_index(self):
        """Load FAISS index and vector ID mapping."""
        index_path = settings.FAISS_INDEX_PATH
        mapping_path = index_path.replace('.bin', '_mapping.npy')
        
        if not Path(index_path).exists():
            print(f"⚠ Warning: FAISS index not found at {index_path}")
            print("  Run 'python build_index.py' to create the index")
            return
        
        # Load index
        self.index = faiss.read_index(index_path)
        print(f"  Loaded FAISS index with {self.index.ntotal} vectors")
        
        # Load vector ID mapping
        if Path(mapping_path).exists():
            self.vector_id_mapping = np.load(mapping_path)
            print(f"  Loaded vector ID mapping")
    
    def _init_llm(self):
        """Initialize LLM client - prioritizes Gemini, falls back to OpenAI."""
        # Try Google Gemini first
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "":
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.llm_client = genai.GenerativeModel('gemini-pro')
                self.llm_type = "gemini"
                print("  Using Google Gemini Pro LLM")
                return
            except Exception as e:
                print(f"  Gemini initialization failed: {e}")
        
        # Fall back to OpenAI
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "":
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.llm_type = "openai"
                print("  Using OpenAI LLM")
                return
            except Exception as e:
                print(f"  OpenAI initialization failed: {e}")
        
        # Use fallback if no API keys
        self.llm_client = None
        self.llm_type = "fallback"
        print("  Using intelligent fallback (no API key provided)")
    
    def _get_data_summary(self, db: Session) -> str:
        """Get a text summary of the current database state."""
        from sqlalchemy import func
        from models import ArgoProfile
        
        count = db.query(func.count(ArgoProfile.id)).scalar()
        floats = db.query(func.count(func.distinct(ArgoProfile.float_id))).scalar()
        
        temp_stats = db.query(func.avg(ArgoProfile.temperature), func.min(ArgoProfile.temperature), func.max(ArgoProfile.temperature)).first()
        sal_stats = db.query(func.avg(ArgoProfile.salinity), func.min(ArgoProfile.salinity), func.max(ArgoProfile.salinity)).first()
        
        summary = f"DATASET SUMMARY: Total of {count} measurements from {floats} unique ARGO floats. "
        if temp_stats[0]:
            summary += f"Temperature Avg: {temp_stats[0]:.2f}C (Range: {temp_stats[1]:.2f} to {temp_stats[2]:.2f}). "
        if sal_stats[0]:
            summary += f"Salinity Avg: {sal_stats[0]:.2f}PSU (Range: {sal_stats[1]:.2f} to {sal_stats[2]:.2f})."
            
        return summary

    def retrieve_context(
        self, 
        query: str, 
        db: Session, 
        top_k: int = 5
    ) -> Tuple[List[str], List[int]]:
        """
        Retrieve relevant context documents and global summary.
        """
        # Get global summary first
        summary = self._get_data_summary(db)
        contexts = [f"GLOBAL STATS: {summary}"]
        
        if self.index is None or self.model is None:
            return contexts, []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Get vector IDs
        retrieved_ids = [int(self.vector_id_mapping[idx]) for idx in indices[0]]
        
        # Fetch documents from database
        documents = db.query(ArgoDocument).filter(
            ArgoDocument.vector_id.in_(retrieved_ids)
        ).all()
        
        # Create document map for ordering
        doc_map = {doc.vector_id: doc.text for doc in documents}
        
        # Add retrieved contexts
        contexts.extend([doc_map.get(vid, "") for vid in retrieved_ids if vid in doc_map])
        
        return contexts, retrieved_ids
    
    def generate_response(
        self, 
        query: str, 
        contexts: List[str]
    ) -> str:
        """
        Generate response using LLM with retrieved context.
        
        Args:
            query: User query
            contexts: Retrieved context documents
            
        Returns:
            Generated response
        """
        if self.llm_type == "gemini" and self.llm_client:
            return self._generate_gemini_response(query, contexts)
        elif self.llm_type == "openai" and self.llm_client:
            return self._generate_openai_response(query, contexts)
        else:
            return self._generate_fallback_response(query, contexts)
    
    def _generate_openai_response(self, query: str, contexts: List[str]) -> str:
        """Generate response using OpenAI API with enhanced context and visualization recommendations."""
        # Build context string
        context_str = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
        
        # Create enhanced system prompt
        system_prompt = """You are ARGO-AI, a world-class Oceanographic Research Assistant. 
        You specialize in multi-dimensional analysis of ARGO float data, understanding thermodynamic properties, salinity gradients, and deep-sea current patterns.

        MISSION: Provide rigorous, data-driven analysis for professional oceanographers.
        
        PROTOCOLS:
        1. SCIENTIFIC RIGOR: Use specific values (temperature in °C, salinity in PSU, depth in meters) from the provided data.
        2. COMPARATIVE ANALYSIS: When multiple floats or profiles are present, compare and contrast their properties.
        3. TREND IDENTIFICATION: Look for vertical gradients (thermoclines, haloclines) or seasonal shifts.
        4. UNCERTAINTY: If data is sparse or geographic coverage is limited, state this explicitly as a researcher would.
        5. VISUALIZATION: Always suggest specific visualizations by their ID:
           - `temperature_distribution`: Histogram of temperatures
           - `salinity_profile`: Depth vs Salinity
           - `ts_diagram`: Temperature vs Salinity scatter (for water mass analysis)
           - `spatial_map`: Spatial density heatmap
           - `trajectory_plot`: Sequential movement of a float

        Format your responses with clear headings, bullet points for data, and a 'Scientific Interpretation' section.
        """
        
        user_prompt = f"""[RESEARCHER QUERY]: {query}

[AVAILABLE DATA CONTEXT]:
{context_str}

[INSTRUCTIONS]:
Analyze the context above to answer the query. If the query asks for comparisons, perform them numerically. If the data points to specific locations (like the North Atlantic or Arctic), provide regional context.

Suggest at least one visualization ID from the following list if it helps illustrate your point: 
`temperature_distribution`, `salinity_profile`, `ts_diagram`, `spatial_map`, `trajectory_plot`.

Response:"""
        
        try:
            # Call OpenAI API with GPT-4o (latest stable model)
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",  # Latest GPT-4 model (more stable and widely available)
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                top_p=0.9
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"OpenAI GPT-4o error: {error_msg}")
            
            # Check if it's a quota issue or model access issue
            if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                print("⚠️ OpenAI API quota exceeded. Please add credits at https://platform.openai.com/account/billing")
                print("   Using intelligent fallback system with retrieved context...")
                return self._generate_fallback_response(query, contexts)
            
            # Try GPT-3.5 as fallback for other errors
            try:
                print("Falling back to GPT-3.5-turbo...")
                response = self.llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=600
                )
                return response.choices[0].message.content
            except Exception as e2:
                print(f"All OpenAI models failed: {e2}")
                print("Using intelligent fallback response system...")
                return self._generate_fallback_response(query, contexts)
    
    def _generate_gemini_response(self, query: str, contexts: List[str]) -> str:
        """Generate response using Google Gemini Pro."""
        context_text = "\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(contexts[:5])])
        
        prompt = f"""You are an expert AI oceanographer assistant analyzing real ARGO float data from the global ocean observation network.

Context from ARGO database (real measurements):
{context_text}

Researcher's question: {query}

Provide a comprehensive answer that:
- Directly addresses the question using the real data provided above
- References specific measurements and values from the context
- Explains relevant oceanographic concepts and patterns
- Suggests appropriate visualizations if they would enhance understanding (e.g., "Show me temperature distribution" or "depth_profile")
- Provides scientific context and interpretation

Be precise, use actual numbers from the data, and speak like an oceanography expert working with real ARGO float measurements."""
        
        try:
            response = self.llm_client.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            print("Falling back to intelligent response system...")
            return self._generate_fallback_response(query, contexts)
    
    def _generate_fallback_response(self, query: str, contexts: List[str]) -> str:
        """Generate intelligent rule-based response with visualization suggestions when LLM unavailable."""
        if not contexts:
            return "I don't have enough data to answer that question. The database may be empty or the query didn't match any records. Try asking about temperature, salinity, or depth measurements."
        
        # Check if this is a greeting or simple query
        query_lower = query.lower().strip()
        greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        if query_lower in greetings or len(query.split()) <= 2 and not any(word in query_lower for word in ['temperature', 'salinity', 'depth', 'data', 'show', 'what', 'how']):
            return f"Hello! I'm your AI Oceanographic Assistant powered by ARGO data. I can help you explore ocean measurements including temperature, salinity, depth profiles, and geographic distributions. Try asking questions like:\n\n• What's the temperature distribution?\n• Show me the correlation between temperature and salinity\n• What are the depth profiles?\n• Show me Arctic data\n\nHow can I assist you today?"
        
        # Extract key information from contexts
        response_parts = [
            "Based on the ARGO oceanographic data, here's what I found:\n"
        ]
        
        # Analyze contexts for key metrics
        temperatures = []
        salinities = []
        depths = []
        pressures = []
        locations = []
        
        import re
        for ctx in contexts[:5]:  # Analyze top 5 contexts
            # Extract temperature
            if "temperature" in ctx.lower():
                temp_match = re.search(r'temperature of ([\d.\-]+)', ctx)
                if temp_match:
                    try:
                        temperatures.append(float(temp_match.group(1)))
                    except:
                        pass
            
            # Extract salinity
            if "salinity" in ctx.lower():
                sal_match = re.search(r'salinity of ([\d.]+)', ctx)
                if sal_match:
                    try:
                        salinities.append(float(sal_match.group(1)))
                    except:
                        pass
            
            # Extract depth
            if "depth" in ctx.lower():
                depth_match = re.search(r'depth ([\d.]+)', ctx)
                if depth_match:
                    try:
                        depths.append(float(depth_match.group(1)))
                    except:
                        pass
            
            # Extract location
            if "latitude" in ctx.lower() and "longitude" in ctx.lower():
                lat_match = re.search(r'latitude ([\d.\-]+)', ctx)
                lon_match = re.search(r'longitude ([\d.\-]+)', ctx)
                if lat_match and lon_match:
                    try:
                        locations.append((float(lat_match.group(1)), float(lon_match.group(1))))
                    except:
                        pass
            
            # Add context snippet
            response_parts.append(f"• {ctx[:250]}")
        
        # Add comprehensive summary statistics (only if data found)
        if temperatures or salinities or depths:
            response_parts.append("\n**Summary Statistics:**")
        
        if temperatures:
            avg_temp = np.mean(temperatures)
            min_temp = np.min(temperatures)
            max_temp = np.max(temperatures)
            std_temp = np.std(temperatures)
            response_parts.append(f"\n🌡️ Temperature: {avg_temp:.2f}°C (range: {min_temp:.2f}°C to {max_temp:.2f}°C, σ={std_temp:.2f})")
        
        if salinities:
            avg_sal = np.mean(salinities)
            min_sal = np.min(salinities)
            max_sal = np.max(salinities)
            response_parts.append(f"\n💧 Salinity: {avg_sal:.2f} PSU (range: {min_sal:.2f} to {max_sal:.2f} PSU)")
        
        if depths:
            avg_depth = np.mean(depths)
            max_depth = np.max(depths)
            response_parts.append(f"\n📊 Depth: Average {avg_depth:.1f}m, Maximum {max_depth:.1f}m")
        
        if locations:
            response_parts.append(f"\n🗺️ Locations: {len(locations)} geographic positions")
        
        # Only suggest visualizations if query explicitly asks for data analysis
        if any(word in query_lower for word in ["show", "visualize", "graph", "chart", "plot", "correlation", "distribution", "histogram", "profile"]):
            if "correlation" in query_lower or "relationship" in query_lower:
                response_parts.append("\n\n💡 Showing scatter_plot to visualize correlations between variables")
            elif "distribution" in query_lower or "histogram" in query_lower:
                response_parts.append("\n\n💡 Generating histogram to show data distribution")
            elif "profile" in query_lower:
                response_parts.append("\n\n💡 Generating depth_profile to show vertical structure")
        
        response_parts.append(f"\n\n📈 Retrieved {len(contexts)} relevant oceanographic measurements.")
        
        return "\n".join(response_parts)
    
    def query(self, query_text: str, db: Session, top_k: int = 5) -> dict:
        """
        Full RAG query pipeline.
        
        Args:
            query_text: User query
            db: Database session
            top_k: Number of documents to retrieve
            
        Returns:
            Dictionary with response and metadata
        """
        # Retrieve context
        contexts, doc_ids = self.retrieve_context(query_text, db, top_k)
        
        # Generate response
        response = self.generate_response(query_text, contexts)
        
        return {
            "query": query_text,
            "response": response,
            "retrieved_contexts": contexts,
            "document_ids": doc_ids,
            "num_contexts": len(contexts)
        }


# Global RAG pipeline instance
_rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create global RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
