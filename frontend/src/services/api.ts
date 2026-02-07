import axios, { AxiosInstance } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ==================== PROJECT APIS ====================

export const projectAPI = {
  createProject: async (
    name: string,
    description?: string,
    fieldTemplateId?: string,
  ) => {
    const response = await apiClient.post("/projects", {
      name,
      description,
      field_template_id: fieldTemplateId,
    });
    return response.data;
  },

  getProject: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}`);
    return response.data;
  },

  listProjects: async (skip = 0, limit = 100) => {
    const response = await apiClient.get("/projects", {
      params: { skip, limit },
    });
    return response.data;
  },

  updateProject: async (
    projectId: string,
    name?: string,
    description?: string,
    fieldTemplateId?: string,
  ) => {
    const response = await apiClient.put(`/projects/${projectId}`, {
      name,
      description,
      field_template_id: fieldTemplateId,
    });
    return response.data;
  },

  deleteProject: async (projectId: string) => {
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response.data;
  },
};

// ==================== DOCUMENT APIS ====================

export const documentAPI = {
  uploadDocument: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.post(
      `/projects/${projectId}/documents/upload`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  listDocuments: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/documents`);
    return response.data;
  },
};

// ==================== FIELD TEMPLATE APIS ====================

export const fieldTemplateAPI = {
  createTemplate: async (name: string, description: string, fields: any[]) => {
    const response = await apiClient.post("/field-templates", {
      name,
      description,
      fields,
    });
    return response.data;
  },

  listTemplates: async () => {
    const response = await apiClient.get("/field-templates");
    return response.data;
  },
};

// ==================== EXTRACTION APIS ====================

export const extractionAPI = {
  extractFields: async (projectId: string, documentId?: string) => {
    const response = await apiClient.post(`/projects/${projectId}/extract`, {
      document_id: documentId,
    });
    return response.data;
  },
};

// ==================== REVIEW APIS ====================

export const reviewAPI = {
  reviewExtraction: async (
    extractionId: string,
    status: string,
    manualValue?: string,
    notes?: string,
  ) => {
    const response = await apiClient.put(
      `/extractions/${extractionId}/review`,
      {
        status,
        manual_value: manualValue,
        reviewer_notes: notes,
      },
    );
    return response.data;
  },

  getPendingReviews: async (projectId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/reviews/pending`,
    );
    return response.data;
  },
};

// ==================== COMPARISON TABLE APIS ====================

export const comparisonAPI = {
  getTable: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/table`);
    return response.data;
  },

  exportCSV: async (projectId: string) => {
    const response = await apiClient.post(
      `/projects/${projectId}/table/export-csv`,
    );
    return response.data;
  },
};

// ==================== EVALUATION APIS ====================

export const evaluationAPI = {
  evaluateProject: async (projectId: string, evaluationData: any) => {
    const response = await apiClient.post(
      `/projects/${projectId}/evaluate`,
      evaluationData,
    );
    return response.data;
  },

  getReport: async (projectId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/evaluation-report`,
    );
    return response.data;
  },
};

// ==================== TASK APIS ====================

export const taskAPI = {
  getStatus: async (taskId: string) => {
    const response = await apiClient.get(`/tasks/${taskId}`);
    return response.data;
  },
};

export default apiClient;
