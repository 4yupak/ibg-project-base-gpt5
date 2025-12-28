import { useState, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Upload, FileSpreadsheet, Link2, Check, X, AlertCircle, 
  RefreshCw, Eye, Clock, ChevronDown, ChevronUp, FileText,
  Building, ArrowLeft, Loader2
} from 'lucide-react';
import { useI18n } from '../i18n';
import { filesApi, projectsApi, pricesApi } from '../services/api';

interface Project {
  id: number;
  name_en: string;
  name_ru: string;
}

interface ParsePreview {
  success: boolean;
  total_units: number;
  valid_units: number;
  invalid_units: number;
  currency: string | null;
  project_name: string | null;
  sample_units: any[];
  warnings: string[];
  error: string | null;
}

interface ProcessingStatus {
  id: number;
  status: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  units_created: number;
  units_updated: number;
  units_unchanged: number;
  units_errors: number;
  errors: Array<{ message: string }> | null;
  warnings: Array<{ message: string }> | null;
}

type SourceType = 'pdf' | 'excel' | 'google_sheets';

export default function PriceIngestionPage() {
  const { t, language } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  
  // State
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(
    searchParams.get('project_id') ? parseInt(searchParams.get('project_id')!) : null
  );
  const [sourceType, setSourceType] = useState<SourceType>('excel');
  const [file, setFile] = useState<File | null>(null);
  const [googleSheetUrl, setGoogleSheetUrl] = useState('');
  const [currency, setCurrency] = useState('THB');
  const [preview, setPreview] = useState<ParsePreview | null>(null);
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(true);
  const [activeVersionId, setActiveVersionId] = useState<number | null>(null);
  
  // Fetch projects
  const { data: projectsData } = useQuery({
    queryKey: ['projects-list'],
    queryFn: () => projectsApi.list({ page_size: 100 }),
  });
  
  // Fetch processing status
  const { data: statusData } = useQuery({
    queryKey: ['price-version-status', activeVersionId],
    queryFn: () => activeVersionId ? filesApi.getIngestionStatus(activeVersionId) : null,
    enabled: !!activeVersionId,
    refetchInterval: (query) => {
      const data = query.state.data as ProcessingStatus | null;
      if (data?.status === 'processing' || data?.status === 'pending') {
        return 2000; // Poll every 2 seconds while processing
      }
      return false;
    },
  });
  
  // Fetch recent versions for selected project
  const { data: versionsData } = useQuery({
    queryKey: ['price-versions', selectedProjectId],
    queryFn: () => selectedProjectId 
      ? pricesApi.versions(selectedProjectId, { page_size: 10 })
      : null,
    enabled: !!selectedProjectId,
  });
  
  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('currency', currency);
      
      const response = await fetch('/api/v1/files/preview', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      return response.json();
    },
    onSuccess: (data) => {
      setPreview(data);
    },
  });
  
  // Ingest mutation
  const ingestMutation = useMutation({
    mutationFn: async () => {
      if (!selectedProjectId) throw new Error('No project selected');
      
      const formData = new FormData();
      formData.append('project_id', selectedProjectId.toString());
      formData.append('source_type', sourceType);
      formData.append('currency', currency);
      formData.append('process_async', 'true');
      
      if (sourceType === 'google_sheets') {
        formData.append('source_url', googleSheetUrl);
      } else if (file) {
        formData.append('file', file);
      }
      
      const response = await fetch('/api/v1/files/ingest-price', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ingestion failed');
      }
      
      return response.json();
    },
    onSuccess: (data) => {
      setActiveVersionId(data.price_version_id);
      setPreview(null);
      setFile(null);
      setGoogleSheetUrl('');
      queryClient.invalidateQueries({ queryKey: ['price-versions'] });
    },
  });
  
  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const ext = droppedFile.name.split('.').pop()?.toLowerCase();
      if (['pdf', 'xlsx', 'xls', 'csv'].includes(ext || '')) {
        setFile(droppedFile);
        setSourceType(ext === 'pdf' ? 'pdf' : 'excel');
        setPreview(null);
      }
    }
  }, []);
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const ext = selectedFile.name.split('.').pop()?.toLowerCase();
      setFile(selectedFile);
      setSourceType(ext === 'pdf' ? 'pdf' : 'excel');
      setPreview(null);
    }
  };
  
  const projects: Project[] = projectsData?.items || [];
  const recentVersions = versionsData?.items || [];
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'approved':
        return 'text-green-600 bg-green-100';
      case 'failed':
      case 'rejected':
        return 'text-red-600 bg-red-100';
      case 'processing':
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'requires_review':
        return 'text-orange-600 bg-orange-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };
  
  const getStatusLabel = (status: string) => {
    const labels: Record<string, { en: string; ru: string }> = {
      pending: { en: 'Pending', ru: 'Ожидает' },
      processing: { en: 'Processing', ru: 'Обработка' },
      completed: { en: 'Completed', ru: 'Завершено' },
      failed: { en: 'Failed', ru: 'Ошибка' },
      requires_review: { en: 'Needs Review', ru: 'Требует проверки' },
      approved: { en: 'Approved', ru: 'Одобрено' },
      rejected: { en: 'Rejected', ru: 'Отклонено' },
    };
    return labels[status]?.[language as keyof typeof labels[string]] || status;
  };
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link 
            to="/analytics" 
            className="text-blue-600 hover:text-blue-700 flex items-center gap-1 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            {language === 'ru' ? 'Назад к аналитике' : 'Back to Analytics'}
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            {language === 'ru' ? 'Загрузка прайсов' : 'Price Ingestion'}
          </h1>
          <p className="text-gray-600 mt-1">
            {language === 'ru' 
              ? 'Загрузите прайс-лист для обновления данных о юнитах'
              : 'Upload price list to update unit data'}
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Upload Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* Project Selection */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-600" />
                {language === 'ru' ? 'Выберите проект' : 'Select Project'}
              </h2>
              
              <select
                value={selectedProjectId || ''}
                onChange={(e) => setSelectedProjectId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">
                  {language === 'ru' ? '-- Выберите проект --' : '-- Select a project --'}
                </option>
                {projects.map((project: Project) => (
                  <option key={project.id} value={project.id}>
                    {language === 'ru' ? project.name_ru : project.name_en}
                  </option>
                ))}
              </select>
            </div>
            
            {selectedProjectId && (
              <>
                {/* Source Type Selection */}
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h2 className="text-lg font-semibold mb-4">
                    {language === 'ru' ? 'Источник данных' : 'Data Source'}
                  </h2>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <button
                      onClick={() => { setSourceType('excel'); setPreview(null); }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        sourceType === 'excel'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <FileSpreadsheet className={`w-8 h-8 mx-auto mb-2 ${
                        sourceType === 'excel' ? 'text-blue-600' : 'text-gray-400'
                      }`} />
                      <p className="text-sm font-medium">Excel / CSV</p>
                    </button>
                    
                    <button
                      onClick={() => { setSourceType('pdf'); setPreview(null); }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        sourceType === 'pdf'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <FileText className={`w-8 h-8 mx-auto mb-2 ${
                        sourceType === 'pdf' ? 'text-blue-600' : 'text-gray-400'
                      }`} />
                      <p className="text-sm font-medium">PDF</p>
                    </button>
                    
                    <button
                      onClick={() => { setSourceType('google_sheets'); setPreview(null); }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        sourceType === 'google_sheets'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <Link2 className={`w-8 h-8 mx-auto mb-2 ${
                        sourceType === 'google_sheets' ? 'text-blue-600' : 'text-gray-400'
                      }`} />
                      <p className="text-sm font-medium">Google Sheets</p>
                    </button>
                  </div>
                </div>
                
                {/* File Upload or URL Input */}
                <div className="bg-white rounded-xl shadow-sm p-6">
                  {sourceType === 'google_sheets' ? (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {language === 'ru' ? 'URL Google Sheets' : 'Google Sheets URL'}
                      </label>
                      <input
                        type="url"
                        value={googleSheetUrl}
                        onChange={(e) => setGoogleSheetUrl(e.target.value)}
                        placeholder="https://docs.google.com/spreadsheets/d/..."
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                      <p className="text-sm text-gray-500 mt-2">
                        {language === 'ru'
                          ? 'Убедитесь, что таблица доступна для чтения'
                          : 'Make sure the sheet is accessible for reading'}
                      </p>
                    </div>
                  ) : (
                    <div
                      onDrop={handleDrop}
                      onDragOver={(e) => e.preventDefault()}
                      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                        file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      {file ? (
                        <div>
                          <Check className="w-12 h-12 text-green-600 mx-auto mb-3" />
                          <p className="font-medium text-gray-900">{file.name}</p>
                          <p className="text-sm text-gray-500 mt-1">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                          <button
                            onClick={() => { setFile(null); setPreview(null); }}
                            className="text-red-600 text-sm mt-3 hover:underline"
                          >
                            {language === 'ru' ? 'Удалить' : 'Remove'}
                          </button>
                        </div>
                      ) : (
                        <div>
                          <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                          <p className="text-gray-600 mb-2">
                            {language === 'ru'
                              ? 'Перетащите файл сюда или'
                              : 'Drag and drop a file here, or'}
                          </p>
                          <label className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium">
                            {language === 'ru' ? 'выберите файл' : 'browse'}
                            <input
                              type="file"
                              accept=".pdf,.xlsx,.xls,.csv"
                              onChange={handleFileSelect}
                              className="hidden"
                            />
                          </label>
                          <p className="text-sm text-gray-500 mt-3">
                            {sourceType === 'pdf' ? 'PDF' : 'Excel, CSV'} (max 50MB)
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Currency Selection */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {language === 'ru' ? 'Валюта в файле' : 'Currency in file'}
                    </label>
                    <select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="THB">THB (Thai Baht)</option>
                      <option value="USD">USD (US Dollar)</option>
                      <option value="EUR">EUR (Euro)</option>
                      <option value="IDR">IDR (Indonesian Rupiah)</option>
                      <option value="RUB">RUB (Russian Ruble)</option>
                    </select>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={() => previewMutation.mutate()}
                      disabled={(!file && sourceType !== 'google_sheets') || previewMutation.isPending}
                      className="flex-1 px-4 py-3 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {previewMutation.isPending ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                      {language === 'ru' ? 'Предпросмотр' : 'Preview'}
                    </button>
                    
                    <button
                      onClick={() => ingestMutation.mutate()}
                      disabled={
                        (!file && sourceType !== 'google_sheets') ||
                        (sourceType === 'google_sheets' && !googleSheetUrl) ||
                        ingestMutation.isPending
                      }
                      className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {ingestMutation.isPending ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Upload className="w-5 h-5" />
                      )}
                      {language === 'ru' ? 'Загрузить' : 'Upload'}
                    </button>
                  </div>
                </div>
                
                {/* Preview Results */}
                {preview && (
                  <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                    <div
                      className="p-4 bg-gray-50 flex items-center justify-between cursor-pointer"
                      onClick={() => setIsPreviewExpanded(!isPreviewExpanded)}
                    >
                      <div className="flex items-center gap-3">
                        <Eye className="w-5 h-5 text-blue-600" />
                        <span className="font-semibold">
                          {language === 'ru' ? 'Результат предпросмотра' : 'Preview Results'}
                        </span>
                        {preview.success ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded">
                            {preview.valid_units} {language === 'ru' ? 'юнитов' : 'units'}
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-sm rounded">
                            {language === 'ru' ? 'Ошибка' : 'Error'}
                          </span>
                        )}
                      </div>
                      {isPreviewExpanded ? <ChevronUp /> : <ChevronDown />}
                    </div>
                    
                    {isPreviewExpanded && (
                      <div className="p-4">
                        {preview.success ? (
                          <>
                            {/* Stats */}
                            <div className="grid grid-cols-4 gap-4 mb-4">
                              <div className="bg-blue-50 p-3 rounded-lg text-center">
                                <p className="text-2xl font-bold text-blue-600">{preview.total_units}</p>
                                <p className="text-sm text-gray-600">
                                  {language === 'ru' ? 'Всего' : 'Total'}
                                </p>
                              </div>
                              <div className="bg-green-50 p-3 rounded-lg text-center">
                                <p className="text-2xl font-bold text-green-600">{preview.valid_units}</p>
                                <p className="text-sm text-gray-600">
                                  {language === 'ru' ? 'Валидных' : 'Valid'}
                                </p>
                              </div>
                              <div className="bg-red-50 p-3 rounded-lg text-center">
                                <p className="text-2xl font-bold text-red-600">{preview.invalid_units}</p>
                                <p className="text-sm text-gray-600">
                                  {language === 'ru' ? 'С ошибками' : 'Invalid'}
                                </p>
                              </div>
                              <div className="bg-gray-50 p-3 rounded-lg text-center">
                                <p className="text-2xl font-bold text-gray-600">{preview.currency || '-'}</p>
                                <p className="text-sm text-gray-600">
                                  {language === 'ru' ? 'Валюта' : 'Currency'}
                                </p>
                              </div>
                            </div>
                            
                            {/* Sample Units Table */}
                            {preview.sample_units.length > 0 && (
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Юнит' : 'Unit'}</th>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Спальни' : 'BR'}</th>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Площадь' : 'Area'}</th>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Этаж' : 'Floor'}</th>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Цена' : 'Price'}</th>
                                      <th className="px-3 py-2 text-left">{language === 'ru' ? 'Статус' : 'Status'}</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {preview.sample_units.map((unit, idx) => (
                                      <tr 
                                        key={idx} 
                                        className={`border-b ${unit.is_invalid ? 'bg-red-50' : ''}`}
                                      >
                                        <td className="px-3 py-2 font-medium">{unit.unit_number}</td>
                                        <td className="px-3 py-2">{unit.bedrooms ?? '-'}</td>
                                        <td className="px-3 py-2">{unit.area_sqm ? `${unit.area_sqm} m²` : '-'}</td>
                                        <td className="px-3 py-2">{unit.floor ?? '-'}</td>
                                        <td className="px-3 py-2">
                                          {unit.price ? unit.price.toLocaleString() : '-'}
                                        </td>
                                        <td className="px-3 py-2">
                                          <span className={`px-2 py-1 rounded text-xs ${
                                            unit.status === 'available' ? 'bg-green-100 text-green-700' :
                                            unit.status === 'sold' ? 'bg-red-100 text-red-700' :
                                            'bg-gray-100 text-gray-700'
                                          }`}>
                                            {unit.status || 'unknown'}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                            
                            {/* Warnings */}
                            {preview.warnings.length > 0 && (
                              <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                                <p className="font-medium text-yellow-700 flex items-center gap-2">
                                  <AlertCircle className="w-4 h-4" />
                                  {language === 'ru' ? 'Предупреждения' : 'Warnings'}
                                </p>
                                <ul className="mt-2 text-sm text-yellow-600 space-y-1">
                                  {preview.warnings.map((w, idx) => (
                                    <li key={idx}>• {w}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="p-4 bg-red-50 rounded-lg">
                            <p className="font-medium text-red-700 flex items-center gap-2">
                              <X className="w-4 h-4" />
                              {language === 'ru' ? 'Ошибка парсинга' : 'Parsing Error'}
                            </p>
                            <p className="text-sm text-red-600 mt-1">{preview.error}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                
                {/* Processing Status */}
                {statusData && (
                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                      <Clock className="w-5 h-5 text-blue-600" />
                      {language === 'ru' ? 'Статус обработки' : 'Processing Status'}
                    </h3>
                    
                    <div className="flex items-center gap-4 mb-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(statusData.status)}`}>
                        {getStatusLabel(statusData.status)}
                      </span>
                      
                      {(statusData.status === 'processing' || statusData.status === 'pending') && (
                        <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                      )}
                    </div>
                    
                    {statusData.status === 'completed' || statusData.status === 'requires_review' ? (
                      <div className="grid grid-cols-4 gap-4">
                        <div className="text-center p-3 bg-green-50 rounded-lg">
                          <p className="text-2xl font-bold text-green-600">{statusData.units_created}</p>
                          <p className="text-sm text-gray-600">{language === 'ru' ? 'Создано' : 'Created'}</p>
                        </div>
                        <div className="text-center p-3 bg-blue-50 rounded-lg">
                          <p className="text-2xl font-bold text-blue-600">{statusData.units_updated}</p>
                          <p className="text-sm text-gray-600">{language === 'ru' ? 'Обновлено' : 'Updated'}</p>
                        </div>
                        <div className="text-center p-3 bg-gray-50 rounded-lg">
                          <p className="text-2xl font-bold text-gray-600">{statusData.units_unchanged}</p>
                          <p className="text-sm text-gray-600">{language === 'ru' ? 'Без изменений' : 'Unchanged'}</p>
                        </div>
                        <div className="text-center p-3 bg-red-50 rounded-lg">
                          <p className="text-2xl font-bold text-red-600">{statusData.units_errors}</p>
                          <p className="text-sm text-gray-600">{language === 'ru' ? 'Ошибки' : 'Errors'}</p>
                        </div>
                      </div>
                    ) : null}
                    
                    {statusData.errors && statusData.errors.length > 0 && (
                      <div className="mt-4 p-3 bg-red-50 rounded-lg">
                        <p className="font-medium text-red-700">{language === 'ru' ? 'Ошибки' : 'Errors'}:</p>
                        <ul className="mt-1 text-sm text-red-600 space-y-1">
                          {statusData.errors.map((e, idx) => (
                            <li key={idx}>• {e.message}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          
          {/* Sidebar - Recent Versions */}
          <div className="space-y-6">
            {selectedProjectId && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-blue-600" />
                  {language === 'ru' ? 'Последние загрузки' : 'Recent Uploads'}
                </h3>
                
                {recentVersions.length > 0 ? (
                  <div className="space-y-3">
                    {recentVersions.map((version: any) => (
                      <div 
                        key={version.id}
                        onClick={() => setActiveVersionId(version.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                          activeVersionId === version.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">v{version.version_number}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(version.status)}`}>
                            {getStatusLabel(version.status)}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500">
                          {version.source_file_name || version.source_type}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(version.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">
                    {language === 'ru' ? 'Нет загрузок' : 'No uploads yet'}
                  </p>
                )}
              </div>
            )}
            
            {/* Help Section */}
            <div className="bg-blue-50 rounded-xl p-6">
              <h3 className="font-semibold mb-3 text-blue-900">
                {language === 'ru' ? 'Поддерживаемые форматы' : 'Supported Formats'}
              </h3>
              <ul className="text-sm text-blue-800 space-y-2">
                <li className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4" />
                  Excel (.xlsx, .xls)
                </li>
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  CSV
                </li>
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  PDF ({language === 'ru' ? 'с таблицами' : 'with tables'})
                </li>
                <li className="flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  Google Sheets
                </li>
              </ul>
              
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-sm text-blue-800">
                  {language === 'ru'
                    ? 'Файл должен содержать колонки: номер юнита, цена. Опционально: площадь, этаж, спальни, статус.'
                    : 'File should contain columns: unit number, price. Optional: area, floor, bedrooms, status.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
