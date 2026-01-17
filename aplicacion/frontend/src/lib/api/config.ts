import axios, { AxiosError, type AxiosResponse } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error(
    'NEXT_PUBLIC_API_BASE_URL no está definido. Configúralo en el entorno del frontend.',
  );
}

// 1. Definimos una clase de error personalizada que guarde el status
export class ApiError extends Error {
  status: number;
  
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
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
    return response.data;
  },
  (error: AxiosError) => {
    if (!error.response) {
      return Promise.reject(new Error('Error de red o servidor no disponible.'));
    }

    const { data, status, statusText } = error.response;
    
    const errorData = data as { detail?: string | { msg?: string }[] };
    const detail = errorData?.detail;

    let errorMessage = `API error ${status} (${statusText})`;

    if (typeof detail === 'string') {
      errorMessage = detail;
    } else if (Array.isArray(detail) && detail.length > 0 && detail[0]?.msg) {
      errorMessage = detail[0].msg;
    }

    // 2. Lanzamos nuestro ApiError con el mensaje Y el status
    return Promise.reject(new ApiError(errorMessage, status));
  }
);