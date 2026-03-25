import React, { useState, useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Send, Bot, User as UserIcon } from 'lucide-react';
import Plot from 'react-plotly.js';
import api from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  charts?: ChartData[];
}

interface ChartData {
  type: 'histogram' | 'scatter' | 'depth_profile' | 'heatmap' | '3d_scatter' | 'line' | 'correlation';
  data: any;
  metadata: {
    title: string;
    xlabel?: string;
    ylabel?: string;
    zlabel?: string;
  };
}

export const ChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hi! I\'m your ARGO ocean data assistant. Ask me anything about temperature, salinity, depth patterns — or request a chart like "show me a temperature histogram".',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Intelligent chart detection from AI response
  const detectChartsFromResponse = (response: string): string[] => {
    const chartTypes: string[] = [];
    const lowerResponse = response.toLowerCase();
    
    if (lowerResponse.includes('temperature_histogram') || 
        (lowerResponse.includes('temperature') && lowerResponse.includes('histogram'))) {
      chartTypes.push('temperature_histogram');
    }
    if (lowerResponse.includes('salinity_histogram') || 
        (lowerResponse.includes('salinity') && lowerResponse.includes('histogram'))) {
      chartTypes.push('salinity_histogram');
    }
    if (lowerResponse.includes('depth_profile')) {
      chartTypes.push('depth_profile');
    }
    if (lowerResponse.includes('scatter_plot') || lowerResponse.includes('scatter plot')) {
      chartTypes.push('scatter_plot');
    }
    if (lowerResponse.includes('heatmap')) {
      chartTypes.push('heatmap');
    }
    if (lowerResponse.includes('3d_scatter') || lowerResponse.includes('3d scatter')) {
      chartTypes.push('3d_scatter');
    }
    if (lowerResponse.includes('time_series') || lowerResponse.includes('line chart')) {
      chartTypes.push('line_chart');
    }
    if (lowerResponse.includes('correlation')) {
      chartTypes.push('correlation');
    }
    
    return chartTypes;
  };

  // Detect charts from user query
  const detectChartsFromQuery = (query: string): string[] => {
    const chartTypes: string[] = [];
    const lowerQuery = query.toLowerCase();
    
    // Histogram triggers
    if (lowerQuery.includes('histogram') || lowerQuery.includes('distribution')) {
      if (lowerQuery.includes('temperature') || lowerQuery.includes('temp')) {
        chartTypes.push('temperature_histogram');
      }
      if (lowerQuery.includes('salinity') || lowerQuery.includes('salt')) {
        chartTypes.push('salinity_histogram');
      }
      if (lowerQuery.includes('depth')) {
        chartTypes.push('depth_histogram');
      }
    }
    
    // Scatter plot triggers
    if (lowerQuery.includes('scatter') || lowerQuery.includes('correlation') || 
        lowerQuery.includes('relationship') || lowerQuery.includes('vs')) {
      chartTypes.push('scatter_plot');
    }
    
    // Depth profile triggers
    if (lowerQuery.includes('profile') || lowerQuery.includes('vertical')) {
      chartTypes.push('depth_profile');
    }
    
    // Heatmap triggers
    if (lowerQuery.includes('heatmap') || lowerQuery.includes('spatial') || 
        (lowerQuery.includes('map') && lowerQuery.includes('distribution'))) {
      chartTypes.push('heatmap');
    }
    
    // 3D scatter triggers
    if (lowerQuery.includes('3d') || lowerQuery.includes('three')) {
      chartTypes.push('3d_scatter');
    }
    
    // Line chart triggers
    if (lowerQuery.includes('trend') || lowerQuery.includes('time') || 
        lowerQuery.includes('sequence')) {
      chartTypes.push('line_chart');
    }
    
    return chartTypes;
  };

  // Fetch chart data from backend
  const fetchChartData = async (chartType: string): Promise<ChartData | null> => {
    try {
      let apiParams: any = {};
      
      if (chartType === 'temperature_histogram') {
        apiParams = { chart_type: 'histogram', variable: 'temperature' };
      } else if (chartType === 'salinity_histogram') {
        apiParams = { chart_type: 'histogram', variable: 'salinity' };
      } else if (chartType === 'depth_histogram') {
        apiParams = { chart_type: 'histogram', variable: 'depth' };
      } else if (chartType === 'scatter_plot') {
        apiParams = { chart_type: 'scatter', variable: 'temperature', variable_y: 'salinity' };
      } else if (chartType === 'depth_profile') {
        apiParams = { chart_type: 'depth_profile', variable: 'temperature' };
      } else if (chartType === 'heatmap') {
        apiParams = { chart_type: 'heatmap', variable: 'temperature' };
      } else if (chartType === '3d_scatter') {
        apiParams = { chart_type: '3d_scatter' };
      } else if (chartType === 'line_chart') {
        apiParams = { chart_type: 'line', variable: 'temperature' };
      } else if (chartType === 'correlation') {
        apiParams = { chart_type: 'correlation' };
      } else {
        return null;
      }
      
      const response = await api.get('/visualization/chart-data', { params: apiParams });
      
      if (response.data.error) {
        console.error('Chart data error:', response.data.error);
        return null;
      }
      
      return {
        type: response.data.chart_type,
        data: response.data,
        metadata: response.data.metadata
      };
    } catch (error) {
      console.error(`Failed to fetch ${chartType}:`, error);
      return null;
    }
  };

  // Render different chart types
  const renderChart = (chart: ChartData) => {
    const { type, data, metadata } = chart;
    
    if (type === 'histogram') {
      return (
        <Plot
          data={[
            {
              type: 'histogram',
              x: data.values,
              nbinsx: 25,
              marker: {
                color: data.variable === 'temperature' ? '#ff634b' : 
                       data.variable === 'salinity' ? '#1ab1ff' : '#9333ea',
                line: { color: 'white', width: 1 }
              },
              name: data.variable
            }
          ]}
          layout={{
            title: metadata.title,
            xaxis: { title: metadata.xlabel },
            yaxis: { title: metadata.ylabel },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            plot_bgcolor: 'rgba(15, 23, 42, 0.5)',
            font: { color: '#e2e8f0' },
            margin: { t: 40, r: 20, b: 50, l: 50 },
            height: 350
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      );
    }
    
    if (type === 'scatter') {
      return (
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'markers',
              x: data.x_values,
              y: data.y_values,
              marker: {
                size: 6,
                color: data.x_values,
                colorscale: 'Viridis',
                showscale: true,
                opacity: 0.7
              },
              text: data.x_values.map((x: number, i: number) => 
                `${data.x_variable}: ${x.toFixed(2)}<br>${data.y_variable}: ${data.y_values[i].toFixed(2)}`
              ),
              hovertemplate: '%{text}<extra></extra>'
            }
          ]}
          layout={{
            title: `${metadata.title} (r=${data.correlation.toFixed(3)})`,
            xaxis: { title: metadata.xlabel },
            yaxis: { title: metadata.ylabel },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            plot_bgcolor: 'rgba(15, 23, 42, 0.5)',
            font: { color: '#e2e8f0' },
            height: 400
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      );
    }
    
    if (type === 'depth_profile') {
      return (
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines+markers',
              x: data.values,
              y: data.depths,
              marker: { size: 4, color: '#1ab1ff' },
              line: { color: '#1ab1ff', width: 2 }
            }
          ]}
          layout={{
            title: metadata.title,
            xaxis: { title: metadata.xlabel },
            yaxis: { title: metadata.ylabel, autorange: 'reversed' },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            plot_bgcolor: 'rgba(15, 23, 42, 0.5)',
            font: { color: '#e2e8f0' },
            height: 450
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      );
    }
    
    if (type === '3d_scatter') {
      return (
        <Plot
          data={[
            {
              type: 'scatter3d',
              mode: 'markers',
              x: data.temperature,
              y: data.salinity,
              z: data.depth,
              marker: {
                size: 4,
                color: data.temperature,
                colorscale: 'Jet',
                showscale: true,
                opacity: 0.8
              }
            }
          ]}
          layout={{
            title: metadata.title,
            scene: {
              xaxis: { title: metadata.xlabel },
              yaxis: { title: metadata.ylabel },
              zaxis: { title: metadata.zlabel }
            },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            font: { color: '#e2e8f0' },
            height: 500
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      );
    }
    
    if (type === 'heatmap') {
      return (
        <Plot
          data={[
            {
              type: 'scattergeo',
              mode: 'markers',
              lon: data.longitudes,
              lat: data.latitudes,
              marker: {
                size: 8,
                color: data.values,
                colorscale: 'Jet',
                showscale: true,
                colorbar: { title: data.variable }
              },
              text: data.values.map((v: number) => `${v.toFixed(2)}`)
            }
          ]}
          layout={{
            title: metadata.title,
            geo: { projection: { type: 'natural earth' } },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            font: { color: '#e2e8f0' },
            height: 450
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      );
    }

    if (type === 'correlation') {
      const variables = data.variables || ['Temp', 'Sal', 'Depth', 'Pressure'];
      const matrix = data.correlation_matrix || [];
      return (
        <Plot
          data={[
            {
              type: 'heatmap',
              z: matrix,
              x: variables,
              y: variables,
              colorscale: 'RdBu',
              zmid: 0,
              showscale: true,
              text: matrix.map((row: number[]) => row.map((v: number) => v.toFixed(3))),
              hovertemplate: '%{y} vs %{x}: %{text}<extra></extra>'
            }
          ]}
          layout={{
            title: metadata.title,
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            plot_bgcolor: 'rgba(15, 23, 42, 0.5)',
            font: { color: '#e2e8f0' },
            height: 400,
            margin: { t: 40, r: 20, b: 80, l: 80 }
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      );
    }

    if (type === 'line') {
      return (
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines+markers',
              x: data.indices,
              y: data.values,
              marker: { size: 3, color: '#ff634b' },
              line: { color: '#ff634b', width: 2 },
              name: data.variable
            }
          ]}
          layout={{
            title: metadata.title,
            xaxis: { title: metadata.xlabel },
            yaxis: { title: metadata.ylabel },
            paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
            plot_bgcolor: 'rgba(15, 23, 42, 0.5)',
            font: { color: '#e2e8f0' },
            height: 350,
            margin: { t: 40, r: 20, b: 50, l: 50 }
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      );
    }
    
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Send message to AI backend
      const response = await api.post('/chat/query', { query: input });
      
      // Detect charts from both query and AI response
      const queryCharts = detectChartsFromQuery(input);
      const responseCharts = detectChartsFromResponse(response.data.response);
      const allCharts = [...new Set([...queryCharts, ...responseCharts])];
      
      // Fetch chart data for all detected charts
      const chartDataPromises = allCharts.map(chartType => fetchChartData(chartType));
      const chartResults = await Promise.all(chartDataPromises);
      const validCharts = chartResults.filter(chart => chart !== null) as ChartData[];
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
        charts: validCharts.length > 0 ? validCharts : undefined
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again or rephrase your question.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 md:px-8 lg:px-16 xl:px-32">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-cyan-400" />
                </div>
              )}
              <div className={`max-w-[min(85%,640px)] space-y-3`}>
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    message.role === 'user'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-800 border border-white/5 text-slate-200'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>

                {/* Charts */}
                {message.charts?.map((chart, idx) => (
                  <div key={idx} className="bg-slate-800 border border-white/5 rounded-2xl p-3 overflow-hidden">
                    {renderChart(chart)}
                  </div>
                ))}
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                  <UserIcon className="w-4 h-4 text-slate-300" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Bot className="w-4 h-4 animate-pulse" />
            Thinking…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-white/10 px-4 py-3 bg-slate-900/60 md:px-8 lg:px-16 xl:px-32">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about ocean data, request charts…"
            className="flex-1 bg-slate-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
