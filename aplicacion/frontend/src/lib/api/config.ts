import axios, { AxiosError, type AxiosResponse } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error(
    'NEXT_PUBLIC_API_BASE_URL no está definido. Configúralo en el entorno del frontend.',
  );
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de Respuesta
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Devolvemos directamente la data para evitar escribir .data en cada llamada
    return response.data;
  },
  (error: AxiosError) => {
    // Si no hay respuesta del servidor (caído, red)
    if (!error.response) {
      return Promise.reject(new Error('Error de red o servidor no disponible.'));
    }

    const { data, status, statusText } = error.response;
    
    // Tratamiento de errores estilo FastAPI
    const errorData = data as { detail?: string | { msg?: string }[] };
    const detail = errorData?.detail;

    let errorMessage = `API error ${status} (${statusText})`;

    if (typeof detail === 'string') {
      errorMessage = detail;
    } else if (Array.isArray(detail) && detail.length > 0 && detail[0]?.msg) {
      errorMessage = detail[0].msg;
    }

    return Promise.reject(new Error(errorMessage));
  }
);