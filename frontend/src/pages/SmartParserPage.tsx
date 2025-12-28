import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  Upload, FileSpreadsheet, Check, X, AlertCircle, 
  ChevronRight, Loader, RefreshCw, Brain, Info,
  CheckCircle2, XCircle, HelpCircle
} from 'lucide-react'
import { parserApi, projectsApi } from '../services/api'
import { useI18n } from '../i18n/useI18n'
import clsx from 'clsx'

interface ColumnDetection {
  index: number
  header: string
  suggested_field: string
  confidence: number
}

interface AvailableField {
  name: string
  label: string
  label_ru: string
  description: string
  required: boolean
}

interface ParseSession {
  session_id: string
  file_name: string
  file_type: string
  total_rows: number
  columns_detected: ColumnDetection[]
  preview_rows: Record<string, unknown>[]
  state: string
}

interface ParsedUnit {
  unit_number: string
  bedrooms: number | null
  bathrooms: number | null
  area_sqm: number | null
  floor: number | null
  building: string | null
  price: number | null
  price_per_sqm: number | null
  currency: string
  layout_type: string | null
  view_type: string | null
  status: string
  is_valid: boolean
}

type Step = 'upload' | 'mapping' | 'preview' | 'result'

export default function SmartParserPage() {
  const { t, language } = useI18n()
  const [step, setStep] = useState<Step>('upload')
  const [session, setSession] = useState<ParseSession | null>(null)
  const [mappings, setMappings] = useState<Map<number, { approved: boolean; field: string }>>(new Map())
  const [parsedUnits, setParsedUnits] = useState<ParsedUnit[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [currency, setCurrency] = useState('THB')
  const [dragActive, setDragActive] = useState(false)

  // Fetch available fields
  const { data: fieldsData } = useQuery({
    queryKey: ['parser-fields'],
    queryFn: parserApi.getAvailableFields,
  })
  const availableFields: AvailableField[] = fieldsData?.fields || []

  // Fetch projects for selection
  const { data: projectsData } = useQuery({
    queryKey: ['projects-list'],
    queryFn: () => projectsApi.list({ page_size: 100 }),
  })
  const projects = projectsData?.items || []

  // Fetch learning stats
  const { data: learningStats } = useQuery({
    queryKey: ['parser-learning-stats'],
    queryFn: parserApi.getLearningStats,
    enabled: step === 'upload',
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => parserApi.upload(file),
    onSuccess: (data: ParseSession) => {
      setSession(data)
      // Initialize mappings from detected columns
      const newMappings = new Map<number, { approved: boolean; field: string }>()
      data.columns_detected.forEach((col) => {
        newMappings.set(col.index, {
          approved: col.confidence >= 0.7,
          field: col.suggested_field,
        })
      })
      setMappings(newMappings)
      setStep('mapping')
    },
  })

  // Confirm mapping mutation
  const confirmMutation = useMutation({
    mutationFn: () => {
      if (!session) throw new Error('No session')
      const mappingsArray = Array.from(mappings.entries()).map(([index, data]) => {
        const detection = session.columns_detected.find(c => c.index === index)
        return {
          column_index: index,
          field: detection?.suggested_field || 'unknown',
          approved: data.approved,
          correct_field: data.approved ? undefined : data.field,
        }
      })
      return parserApi.confirmMappings(session.session_id, mappingsArray)
    },
    onSuccess: () => {
      setStep('preview')
    },
  })

  // Parse mutation
  const parseMutation = useMutation({
    mutationFn: () => {
      if (!session) throw new Error('No session')
      return parserApi.parse(session.session_id, selectedProjectId || undefined, currency)
    },
    onSuccess: (data) => {
      setParsedUnits(data.units || [])
      setStep('result')
    },
  })

  // File handling
  const handleFile = useCallback((file: File) => {
    uploadMutation.mutate(file)
  }, [uploadMutation])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }, [handleFile])

  // Mapping handlers
  const toggleApproval = (index: number) => {
    const current = mappings.get(index)
    if (current) {
      setMappings(new Map(mappings.set(index, { ...current, approved: !current.approved })))
    }
  }

  const changeField = (index: number, newField: string) => {
    const current = mappings.get(index)
    if (current) {
      setMappings(new Map(mappings.set(index, { ...current, field: newField, approved: false })))
    }
  }

  // Reset
  const handleReset = () => {
    setStep('upload')
    setSession(null)
    setMappings(new Map())
    setParsedUnits([])
  }

  // Get confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100'
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getFieldLabel = (fieldName: string): string => {
    const field = availableFields.find(f => f.name === fieldName)
    if (!field) return fieldName
    return language === 'ru' ? field.label_ru : field.label
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {language === 'ru' ? 'Умный парсер прайсов' : 'Smart Price Parser'}
          </h1>
          <p className="text-gray-600 mt-1">
            {language === 'ru' 
              ? 'Загрузите файл и подтвердите колонки - парсер учится на ваших исправлениях'
              : 'Upload a file and confirm columns - the parser learns from your corrections'}
          </p>
        </div>
        
        {step !== 'upload' && (
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
          >
            <RefreshCw className="w-4 h-4" />
            {language === 'ru' ? 'Начать заново' : 'Start Over'}
          </button>
        )}
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {(['upload', 'mapping', 'preview', 'result'] as Step[]).map((s, idx) => (
          <div key={s} className="flex items-center">
            <div className={clsx(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
              step === s ? 'bg-blue-100 text-blue-700' : 
              (['upload', 'mapping', 'preview', 'result'].indexOf(step) > idx) 
                ? 'bg-green-100 text-green-700' 
                : 'bg-gray-100 text-gray-500'
            )}>
              {['upload', 'mapping', 'preview', 'result'].indexOf(step) > idx ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <span className="w-5 h-5 flex items-center justify-center rounded-full bg-current/20">
                  {idx + 1}
                </span>
              )}
              {s === 'upload' && (language === 'ru' ? 'Загрузка' : 'Upload')}
              {s === 'mapping' && (language === 'ru' ? 'Маппинг' : 'Mapping')}
              {s === 'preview' && (language === 'ru' ? 'Превью' : 'Preview')}
              {s === 'result' && (language === 'ru' ? 'Результат' : 'Result')}
            </div>
            {idx < 3 && <ChevronRight className="w-4 h-4 text-gray-400 mx-1" />}
          </div>
        ))}
      </div>

      {/* Learning Stats Banner */}
      {step === 'upload' && learningStats && learningStats.total_feedbacks > 0 && (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4 flex items-center gap-4">
          <Brain className="w-8 h-8 text-purple-600" />
          <div>
            <h3 className="font-semibold text-purple-900">
              {language === 'ru' ? 'Парсер обучен' : 'Parser Trained'}
            </h3>
            <p className="text-sm text-purple-700">
              {language === 'ru' 
                ? `${learningStats.patterns_learned} паттернов изучено, точность ${Math.round(learningStats.accuracy_rate * 100)}%`
                : `${learningStats.patterns_learned} patterns learned, ${Math.round(learningStats.accuracy_rate * 100)}% accuracy`}
            </p>
          </div>
        </div>
      )}

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <div 
          className={clsx(
            'border-2 border-dashed rounded-xl p-12 text-center transition-colors',
            dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400',
            uploadMutation.isPending && 'opacity-50 pointer-events-none'
          )}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          {uploadMutation.isPending ? (
            <div className="flex flex-col items-center gap-4">
              <Loader className="w-12 h-12 text-blue-500 animate-spin" />
              <p className="text-gray-600">
                {language === 'ru' ? 'Анализ файла...' : 'Analyzing file...'}
              </p>
            </div>
          ) : (
            <>
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {language === 'ru' ? 'Перетащите файл сюда' : 'Drag and drop your file here'}
              </h3>
              <p className="text-gray-500 mb-4">
                {language === 'ru' ? 'или' : 'or'}
              </p>
              <label className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700">
                <FileSpreadsheet className="w-5 h-5" />
                {language === 'ru' ? 'Выбрать файл' : 'Select File'}
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.xlsx,.xls,.csv"
                  onChange={handleFileInput}
                />
              </label>
              <p className="text-sm text-gray-400 mt-4">
                PDF, Excel (.xlsx, .xls), CSV • Max 50MB
              </p>
            </>
          )}
          
          {uploadMutation.isError && (
            <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {(uploadMutation.error as Error)?.message || 'Upload failed'}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Column Mapping */}
      {step === 'mapping' && session && (
        <div className="space-y-6">
          {/* File Info */}
          <div className="bg-gray-50 rounded-lg p-4 flex items-center gap-4">
            <FileSpreadsheet className="w-8 h-8 text-blue-600" />
            <div>
              <h3 className="font-medium">{session.file_name}</h3>
              <p className="text-sm text-gray-500">
                {session.total_rows} {language === 'ru' ? 'строк' : 'rows'} • 
                {session.columns_detected.length} {language === 'ru' ? 'колонок' : 'columns'}
              </p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">
                {language === 'ru' ? 'Подтвердите маппинг колонок' : 'Confirm Column Mapping'}
              </p>
              <p>
                {language === 'ru' 
                  ? 'Отметьте ✓ если поле определено верно, или выберите правильное поле из списка. Парсер запомнит ваши исправления.'
                  : 'Click ✓ if the field is correct, or select the correct field from the dropdown. The parser will learn from your corrections.'}
              </p>
            </div>
          </div>

          {/* Column Mapping Table */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {language === 'ru' ? 'Заголовок' : 'Header'}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {language === 'ru' ? 'Определено как' : 'Detected As'}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {language === 'ru' ? 'Уверенность' : 'Confidence'}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {language === 'ru' ? 'Поле' : 'Field'}
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">
                    {language === 'ru' ? 'Верно?' : 'Correct?'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {session.columns_detected.map((col) => {
                  const mapping = mappings.get(col.index)
                  return (
                    <tr key={col.index} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                          {col.header}
                        </code>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {getFieldLabel(col.suggested_field)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                          getConfidenceColor(col.confidence)
                        )}>
                          {Math.round(col.confidence * 100)}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={mapping?.field || col.suggested_field}
                          onChange={(e) => changeField(col.index, e.target.value)}
                          className="block w-full rounded-md border-gray-300 shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          {availableFields.map((field) => (
                            <option key={field.name} value={field.name}>
                              {language === 'ru' ? field.label_ru : field.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => toggleApproval(col.index)}
                          className={clsx(
                            'p-2 rounded-full transition-colors',
                            mapping?.approved 
                              ? 'bg-green-100 text-green-600 hover:bg-green-200' 
                              : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                          )}
                        >
                          {mapping?.approved ? (
                            <Check className="w-5 h-5" />
                          ) : (
                            <X className="w-5 h-5" />
                          )}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Preview Table */}
          {session.preview_rows.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-medium text-gray-900">
                {language === 'ru' ? 'Превью данных' : 'Data Preview'}
              </h3>
              <div className="overflow-x-auto border rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {session.columns_detected.map((col) => (
                        <th key={col.index} className="px-3 py-2 text-left font-medium text-gray-600 whitespace-nowrap">
                          {col.header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {session.preview_rows.slice(0, 5).map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        {session.columns_detected.map((col) => (
                          <td key={col.index} className="px-3 py-2 whitespace-nowrap">
                            {String(row[col.header] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <button
              onClick={handleReset}
              className="px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              {language === 'ru' ? 'Отмена' : 'Cancel'}
            </button>
            <button
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {confirmMutation.isPending && <Loader className="w-4 h-4 animate-spin" />}
              {language === 'ru' ? 'Подтвердить маппинг' : 'Confirm Mapping'}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview & Parse */}
      {step === 'preview' && session && (
        <div className="space-y-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-green-600" />
            <div>
              <h3 className="font-medium text-green-900">
                {language === 'ru' ? 'Маппинг сохранён' : 'Mapping Saved'}
              </h3>
              <p className="text-sm text-green-700">
                {language === 'ru' 
                  ? 'Парсер запомнил ваши настройки для будущих файлов'
                  : 'The parser has learned your preferences for future files'}
              </p>
            </div>
          </div>

          {/* Project Selection */}
          <div className="bg-white rounded-lg border p-6 space-y-4">
            <h3 className="font-medium text-gray-900">
              {language === 'ru' ? 'Настройки парсинга' : 'Parsing Settings'}
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {language === 'ru' ? 'Проект (опционально)' : 'Project (optional)'}
                </label>
                <select
                  value={selectedProjectId || ''}
                  onChange={(e) => setSelectedProjectId(e.target.value ? Number(e.target.value) : null)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">
                    {language === 'ru' ? '— Не выбран —' : '— Not selected —'}
                  </option>
                  {projects.map((p: { id: number; name_en: string; name_ru: string }) => (
                    <option key={p.id} value={p.id}>
                      {language === 'ru' ? p.name_ru || p.name_en : p.name_en}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {language === 'ru' ? 'Валюта' : 'Currency'}
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="THB">THB (Thai Baht)</option>
                  <option value="USD">USD (US Dollar)</option>
                  <option value="IDR">IDR (Indonesian Rupiah)</option>
                  <option value="RUB">RUB (Russian Ruble)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <button
              onClick={() => setStep('mapping')}
              className="px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              {language === 'ru' ? 'Назад' : 'Back'}
            </button>
            <button
              onClick={() => parseMutation.mutate()}
              disabled={parseMutation.isPending}
              className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {parseMutation.isPending && <Loader className="w-4 h-4 animate-spin" />}
              {language === 'ru' ? 'Парсить данные' : 'Parse Data'}
            </button>
          </div>
          
          {parseMutation.isError && (
            <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {(parseMutation.error as Error)?.message || 'Parsing failed'}
            </div>
          )}
        </div>
      )}

      {/* Step 4: Results */}
      {step === 'result' && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border p-4">
              <div className="text-3xl font-bold text-gray-900">{parsedUnits.length}</div>
              <div className="text-sm text-gray-500">
                {language === 'ru' ? 'Всего юнитов' : 'Total Units'}
              </div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-3xl font-bold text-green-600">
                {parsedUnits.filter(u => u.is_valid).length}
              </div>
              <div className="text-sm text-gray-500">
                {language === 'ru' ? 'Валидных' : 'Valid'}
              </div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-3xl font-bold text-red-600">
                {parsedUnits.filter(u => !u.is_valid).length}
              </div>
              <div className="text-sm text-gray-500">
                {language === 'ru' ? 'С ошибками' : 'With Errors'}
              </div>
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Unit</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">BR</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Area</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Floor</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Price</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-600">Valid</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {parsedUnits.slice(0, 50).map((unit, idx) => (
                    <tr key={idx} className={clsx(
                      'hover:bg-gray-50',
                      !unit.is_valid && 'bg-red-50'
                    )}>
                      <td className="px-4 py-3 font-medium">{unit.unit_number}</td>
                      <td className="px-4 py-3">{unit.layout_type || '-'}</td>
                      <td className="px-4 py-3">{unit.bedrooms ?? '-'}</td>
                      <td className="px-4 py-3">{unit.area_sqm ? `${unit.area_sqm} m²` : '-'}</td>
                      <td className="px-4 py-3">{unit.floor ?? '-'}</td>
                      <td className="px-4 py-3">
                        {unit.price ? `${unit.price.toLocaleString()} ${unit.currency}` : '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'inline-flex px-2 py-0.5 rounded text-xs font-medium',
                          unit.status === 'available' ? 'bg-green-100 text-green-700' :
                          unit.status === 'sold' ? 'bg-red-100 text-red-700' :
                          unit.status === 'reserved' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-700'
                        )}>
                          {unit.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {unit.is_valid ? (
                          <CheckCircle2 className="w-5 h-5 text-green-600 mx-auto" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-600 mx-auto" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {parsedUnits.length > 50 && (
              <div className="px-4 py-3 bg-gray-50 text-sm text-gray-500 text-center">
                {language === 'ru' 
                  ? `Показаны первые 50 из ${parsedUnits.length} юнитов`
                  : `Showing first 50 of ${parsedUnits.length} units`}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-between">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              <RefreshCw className="w-4 h-4" />
              {language === 'ru' ? 'Загрузить другой файл' : 'Upload Another File'}
            </button>
            
            <div className="flex gap-4">
              <button
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                {language === 'ru' ? 'Экспорт CSV' : 'Export CSV'}
              </button>
              <button
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {language === 'ru' ? 'Сохранить в базу' : 'Save to Database'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
