import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Upload, Table, Eye, BarChart3, Settings, RefreshCw, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { projectAPI, documentAPI, extractionAPI, comparisonAPI } from '../services/api';
import { useStore } from '../store/appStore';
import DocumentUploadSection from '../components/DocumentUploadSection';
import ComparisonTableView from '../components/ComparisonTableView';
import ReviewPanel from '../components/ReviewPanel';
import EvaluationReport from '../components/EvaluationReport';

export const ProjectDetailPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, setCurrentProject, activeTab, setActiveTab, isLoading, setIsLoading } = useStore();
  const [documents, setDocuments] = useState<any[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [tableData, setTableData] = useState<any>(null);

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const loadProject = async () => {
    setIsLoading(true);
    try {
      const project = await projectAPI.getProject(projectId!);
      setCurrentProject(project);
      await loadDocuments();
    } catch (error) {
      toast.error('Failed to load project');
      navigate('/projects');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await documentAPI.listDocuments(projectId!);
      setDocuments(data.documents || []);
    } catch (error) {
      toast.error('Failed to load documents');
    }
  };

  const handleDocumentUpload = async (files: FileList) => {
    if (!files || files.length === 0) return;

    setIsLoading(true);
    try {
      const failedUploads: { name: string; reason: string }[] = [];
      const fileArray = Array.from(files);
      
      // Process strictly one by one to ensure reliability and avoid database locks
      const BATCH_SIZE = 1;
      for (let i = 0; i < fileArray.length; i += BATCH_SIZE) {
        const batch = fileArray.slice(i, i + BATCH_SIZE);
        await Promise.all(
          batch.map(async (file) => {
            try {
              await documentAPI.uploadDocument(projectId!, file);
              toast.success(`Uploaded ${file.name}`);
            } catch (error: any) {
              const reason =
                error?.response?.data?.detail ||
                error?.message ||
                'Upload failed';
              failedUploads.push({ name: file.name, reason });
            }
          })
        );
      }

      await loadDocuments();
      if (failedUploads.length > 0) {
        const names = failedUploads.map((item) => item.name).join(', ');
        const reason = failedUploads[0].reason;
        toast.error(`Failed to upload ${failedUploads.length} files: ${names}. Last error: ${reason}`);
      }
    } catch (error) {
      toast.error('Failed to upload documents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExtractFields = async () => {
    setExtracting(true);
    try {
      const result = await extractionAPI.extractFields(projectId!);
      toast.success('Extraction started - check task status');
    } catch (error) {
      toast.error('Failed to start extraction');
    } finally {
      setExtracting(false);
    }
  };

  const loadComparisonTable = async () => {
    setIsLoading(true);
    try {
      const data = await comparisonAPI.getTable(projectId!);
      setTableData(data);
      setActiveTab('table');
    } catch (error) {
      toast.error('Failed to load comparison table');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectId) return;
    const confirmed = window.confirm('Are you sure you want to delete this project? This action cannot be undone.');
    if (!confirmed) return;
    setIsLoading(true);
    try {
      await projectAPI.deleteProject(projectId);
      toast.success('Project deleted');
      navigate('/projects');
    } catch (error) {
      toast.error('Failed to delete project');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !currentProject) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-gray-500">Loading project...</div>
      </div>
    );
  }

  if (!currentProject) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{currentProject.name}</h1>
              <p className="text-gray-600 mt-2">{currentProject.description}</p>
              <div className="mt-4 flex gap-6 text-sm text-gray-600">
                <span>📁 {documents.length} documents</span>
                <span>✓ {currentProject.extraction_count} extractions</span>
                <span>Status: <span className="font-semibold">{currentProject.status}</span></span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadProject}
                className="flex items-center gap-2 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                <RefreshCw size={18} />
                Refresh
              </button>
              <button
                onClick={handleDeleteProject}
                className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
              >
                <Trash2 size={18} />
                Delete Project
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-4 mb-8 border-b border-gray-200">
          {[
            { id: 'documents', label: 'Documents', icon: Upload },
            { id: 'table', label: 'Comparison Table', icon: Table },
            { id: 'review', label: 'Review', icon: Eye },
            { id: 'evaluation', label: 'Evaluation', icon: BarChart3 },
            { id: 'settings', label: 'Settings', icon: Settings },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => {
                setActiveTab(id);
                if (id === 'table') loadComparisonTable();
              }}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div>
          {activeTab === 'documents' && (
            <div className="space-y-6">
              <DocumentUploadSection
                onUpload={handleDocumentUpload}
                isLoading={isLoading}
              />

              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Uploaded Documents</h2>
                {documents.length === 0 ? (
                  <p className="text-gray-500">No documents uploaded yet</p>
                ) : (
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex justify-between items-center p-4 bg-gray-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-gray-900">{doc.filename}</p>
                          <p className="text-sm text-gray-600">
                            {(doc.file_size / 1024).toFixed(2)} KB · {doc.file_type}
                          </p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            doc.status === 'INDEXED'
                              ? 'bg-green-100 text-green-800'
                              : doc.status === 'ERROR'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Extract Fields</h2>
                <p className="text-gray-600 mb-4">
                  Extract key fields from all documents using the configured field template.
                </p>
                <button
                  onClick={handleExtractFields}
                  disabled={extracting || documents.length === 0}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {extracting ? 'Extracting...' : 'Start Extraction'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'table' && tableData && (
            <ComparisonTableView data={tableData} projectId={projectId!} />
          )}

          {activeTab === 'review' && (
            <ReviewPanel projectId={projectId!} />
          )}

          {activeTab === 'evaluation' && (
            <EvaluationReport projectId={projectId!} />
          )}

          {activeTab === 'settings' && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Project Settings</h2>
              <p className="text-gray-600">Project settings and configuration options coming soon.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
