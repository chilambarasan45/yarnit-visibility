import axios from 'axios';

const api = axios.create({
  baseURL: 'https://yarnit-visibility-3.onrender.com/api',
  headers: {
    'X-API-Key': process.env.REACT_APP_API_KEY || '',
  },
});

export default api;
