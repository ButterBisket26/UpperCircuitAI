import axios from 'axios';

// Pull from Vite environment or default to local FastAPI port
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  /**
   * Submits a question along with optional scope filters.
   */
  query: async (question, ticker = null, reportType = null, fiscalPeriod = null) => {
    const filters = {};
    if (ticker) filters.ticker = ticker;
    if (reportType) filters.report_type = reportType;
    if (fiscalPeriod) filters.fiscal_period = fiscalPeriod;
    
    const response = await client.post('/query', {
      question,
      filters: Object.keys(filters).length > 0 ? filters : null,
    });
    return response.data;
  },

  /**
   * Triggers background web scraper ingestion task.
   */
  ingest: async (ticker, exchange, reportType, fiscalPeriod) => {
    const response = await client.post('/ingest', {
      ticker,
      exchange,
      report_type: reportType,
      fiscal_period: fiscalPeriod,
    });
    return response.data;
  },

  /**
   * Uploads a local PDF report using multipart/form-data.
   */
  upload: async (ticker, exchange, reportType, fiscalPeriod, file, onUploadProgress = null) => {
    const formData = new FormData();
    formData.append('ticker', ticker);
    formData.append('exchange', exchange);
    formData.append('report_type', reportType);
    formData.append('fiscal_period', fiscalPeriod);
    formData.append('file', file);

    const response = await client.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(percent);
        }
      },
    });
    return response.data;
  },

  /**
   * Fetches the complete list of indexed companies.
   */
  listCompanies: async () => {
    const response = await client.get('/companies');
    return response.data;
  },

  /**
   * Fetches filings listed under a ticker.
   */
  listFilings: async (ticker) => {
    const response = await client.get(`/companies/${ticker}/filings`);
    return response.data;
  },

  /**
   * Deletes a filing report.
   */
  deleteFiling: async (filingId) => {
    const response = await client.delete(`/companies/filings/${filingId}`);
    return response.data;
  },

  /**
   * Triggers the pipeline evaluation metrics calculations.
   */
  runEval: async () => {
    const response = await client.post('/eval');
    return response.data;
  },

  /**
   * Checks if there are active ingestion tasks.
   */
  checkIngestStatus: async () => {
    const response = await client.get('/ingest/status');
    return response.data;
  },
};

export default api;
