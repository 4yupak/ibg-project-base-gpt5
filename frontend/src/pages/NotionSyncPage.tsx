import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notionApi, filesApi, projectsApi } from '../services/api'
import { useI18n } from '../i18n'

interface NotionConnectionStatus {
  success: boolean
  database_id?: string
  title?: string
  properties_count?: number
  properties?: string[]
  error?: string
}

interface SyncResult {
  success: boolean
  projects_created: number
  projects_updated: number
  projects_skipped: number
  projects_failed: number
  errors: string[]
  warnings: string[]
  price_files_found: Array<{
    project_name: string
    notion_page_id: string
    price_urls: string[]
  }>
  synced_at: string
}

interface FieldMapping {
  notion_field: string
  propbase_field: string
  notion_type: string
  description: string
  required: boolean
}

interface PreviewProject {
  notion_page_id: string
  name: string
  parsed_data: Record<string, unknown>
  price_list_urls: string[]
  layout_urls: string[]
  gallery_urls: string[]
  errors: string[]
}

interface SchemaProperty {
  type: string
  id: string
  options?: string[]
}

export default function NotionSyncPage() {
  const { t, lang: language } = useI18n()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'status' | 'mapping' | 'preview' | 'sync'>('status')
  const [syncInProgress, setSyncInProgress] = useState(false)
  const [lastSyncResult, setLastSyncResult] = useState<SyncResult | null>(null)

  // Queries
  const { data: connectionStatus, isLoading: isLoadingConnection, refetch: refetchConnection } = useQuery({
    queryKey: ['notion-connection'],
    queryFn: notionApi.testConnection,
    retry: false,
  })

  const { data: configStatus } = useQuery({
    queryKey: ['notion-config'],
    queryFn: notionApi.getConfigStatus,
  })

  const { data: schema } = useQuery({
    queryKey: ['notion-schema'],
    queryFn: notionApi.getSchema,
    enabled: connectionStatus?.success === true,
  })

  const { data: fieldMapping } = useQuery({
    queryKey: ['notion-field-mapping'],
    queryFn: notionApi.getFieldMapping,
  })

  const { data: preview, isLoading: isLoadingPreview, refetch: refetchPreview } = useQuery({
    queryKey: ['notion-preview'],
    queryFn: () => notionApi.preview(5),
    enabled: false, // Manual trigger
  })

  const { data: priceFiles } = useQuery({
    queryKey: ['notion-price-files'],
    queryFn: notionApi.getPriceFiles,
    enabled: connectionStatus?.success === true,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects-list'],
    queryFn: () => projectsApi.list({ limit: 100 }),
  })

  // Mutations
  const syncMutation = useMutation({
    mutationFn: (dryRun: boolean) => notionApi.syncAll(dryRun),
    onSuccess: (data) => {
      setLastSyncResult(data)
      setSyncInProgress(false)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['notion-price-files'] })
    },
    onError: (error) => {
      console.error('Sync error:', error)
      setSyncInProgress(false)
    },
  })

  const handleSync = (dryRun: boolean = false) => {
    setSyncInProgress(true)
    syncMutation.mutate(dryRun)
  }

  const handlePreview = () => {
    refetchPreview()
  }

  // Translations
  const texts = {
    ru: {
      title: 'Интеграция с Notion',
      subtitle: 'Синхронизация проектов из базы Notion',
      tabs: {
        status: 'Статус подключения',
        mapping: 'Сопоставление полей',
        preview: 'Предпросмотр',
        sync: 'Синхронизация',
      },
      connection: {
        title: 'Подключение к Notion',
        testing: 'Проверка подключения...',
        connected: 'Подключено',
        disconnected: 'Не подключено',
        database: 'База данных',
        propertiesCount: 'Количество полей',
        retry: 'Проверить снова',
      },
      config: {
        title: 'Конфигурация',
        apiKey: 'API ключ',
        databaseId: 'ID базы данных',
        configured: 'Настроен',
        notConfigured: 'Не настроен',
      },
      mapping: {
        title: 'Сопоставление полей',
        subtitle: 'Как поля Notion маппятся на поля PropBase',
        notionField: 'Поле Notion',
        propbaseField: 'Поле PropBase',
        type: 'Тип',
        description: 'Описание',
        required: 'Обязательное',
      },
      preview: {
        title: 'Предпросмотр данных',
        subtitle: 'Первые 5 проектов из Notion',
        load: 'Загрузить предпросмотр',
        loading: 'Загрузка...',
        total: 'Всего проектов в Notion',
        project: 'Проект',
        priceFiles: 'Файлы прайсов',
        layouts: 'Планировки',
        gallery: 'Галерея',
        errors: 'Ошибки парсинга',
      },
      sync: {
        title: 'Синхронизация',
        subtitle: 'Импорт проектов из Notion в PropBase',
        dryRun: 'Тестовый прогон',
        dryRunDesc: 'Проверить без сохранения изменений',
        fullSync: 'Полная синхронизация',
        fullSyncDesc: 'Создать/обновить все проекты',
        inProgress: 'Синхронизация...',
        result: 'Результат синхронизации',
        created: 'Создано',
        updated: 'Обновлено',
        skipped: 'Пропущено',
        failed: 'Ошибок',
        priceFilesFound: 'Найдено файлов прайсов',
        errors: 'Ошибки',
        warnings: 'Предупреждения',
        syncedAt: 'Время синхронизации',
      },
      priceFiles: {
        title: 'Файлы прайсов',
        subtitle: 'Прайс-листы, найденные в Notion',
        project: 'Проект',
        files: 'Файлы',
        parse: 'Парсить',
        noPrices: 'Нет файлов прайсов',
      },
      schema: {
        title: 'Схема базы Notion',
        property: 'Свойство',
        type: 'Тип',
        options: 'Опции',
      },
    },
    en: {
      title: 'Notion Integration',
      subtitle: 'Sync projects from Notion database',
      tabs: {
        status: 'Connection Status',
        mapping: 'Field Mapping',
        preview: 'Preview',
        sync: 'Synchronization',
      },
      connection: {
        title: 'Notion Connection',
        testing: 'Testing connection...',
        connected: 'Connected',
        disconnected: 'Not connected',
        database: 'Database',
        propertiesCount: 'Properties count',
        retry: 'Retry',
      },
      config: {
        title: 'Configuration',
        apiKey: 'API Key',
        databaseId: 'Database ID',
        configured: 'Configured',
        notConfigured: 'Not configured',
      },
      mapping: {
        title: 'Field Mapping',
        subtitle: 'How Notion fields map to PropBase fields',
        notionField: 'Notion Field',
        propbaseField: 'PropBase Field',
        type: 'Type',
        description: 'Description',
        required: 'Required',
      },
      preview: {
        title: 'Data Preview',
        subtitle: 'First 5 projects from Notion',
        load: 'Load Preview',
        loading: 'Loading...',
        total: 'Total projects in Notion',
        project: 'Project',
        priceFiles: 'Price Files',
        layouts: 'Layouts',
        gallery: 'Gallery',
        errors: 'Parsing Errors',
      },
      sync: {
        title: 'Synchronization',
        subtitle: 'Import projects from Notion to PropBase',
        dryRun: 'Dry Run',
        dryRunDesc: 'Check without saving changes',
        fullSync: 'Full Sync',
        fullSyncDesc: 'Create/update all projects',
        inProgress: 'Syncing...',
        result: 'Sync Result',
        created: 'Created',
        updated: 'Updated',
        skipped: 'Skipped',
        failed: 'Failed',
        priceFilesFound: 'Price files found',
        errors: 'Errors',
        warnings: 'Warnings',
        syncedAt: 'Synced at',
      },
      priceFiles: {
        title: 'Price Files',
        subtitle: 'Price lists found in Notion',
        project: 'Project',
        files: 'Files',
        parse: 'Parse',
        noPrices: 'No price files',
      },
      schema: {
        title: 'Notion Database Schema',
        property: 'Property',
        type: 'Type',
        options: 'Options',
      },
    },
  }

  const txt = texts[language as keyof typeof texts] || texts.en

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{txt.title}</h1>
        <p className="text-gray-500 mt-1">{txt.subtitle}</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {(['status', 'mapping', 'preview', 'sync'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {txt.tabs[tab]}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'status' && (
        <div className="space-y-6">
          {/* Connection Status */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">{txt.connection.title}</h2>
            
            {isLoadingConnection ? (
              <div className="flex items-center space-x-2 text-gray-500">
                <i className="fas fa-spinner fa-spin"></i>
                <span>{txt.connection.testing}</span>
              </div>
            ) : connectionStatus?.success ? (
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-green-600">
                  <i className="fas fa-check-circle text-xl"></i>
                  <span className="font-medium">{txt.connection.connected}</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">{txt.connection.database}:</span>
                    <p className="font-medium">{connectionStatus.title}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">{txt.connection.propertiesCount}:</span>
                    <p className="font-medium">{connectionStatus.properties_count}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-red-600">
                  <i className="fas fa-times-circle text-xl"></i>
                  <span className="font-medium">{txt.connection.disconnected}</span>
                </div>
                {connectionStatus?.error && (
                  <p className="text-sm text-red-500">{connectionStatus.error}</p>
                )}
                <button
                  onClick={() => refetchConnection()}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {txt.connection.retry}
                </button>
              </div>
            )}
          </div>

          {/* Configuration Status */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">{txt.config.title}</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span>{txt.config.apiKey}</span>
                {configStatus?.api_key_configured ? (
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                    {txt.config.configured}
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                    {txt.config.notConfigured}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span>{txt.config.databaseId}</span>
                {configStatus?.database_id_configured ? (
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                    {txt.config.configured}
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                    {txt.config.notConfigured}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Schema */}
          {connectionStatus?.success && schema?.properties && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">{txt.schema.title}</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {txt.schema.property}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {txt.schema.type}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {txt.schema.options}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {Object.entries(schema.properties as Record<string, SchemaProperty>).map(([name, prop]) => (
                      <tr key={name} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{name}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {prop.type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {prop.options && prop.options.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {prop.options.slice(0, 5).map((opt, i) => (
                                <span key={i} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                                  {opt}
                                </span>
                              ))}
                              {prop.options.length > 5 && (
                                <span className="text-xs text-gray-400">
                                  +{prop.options.length - 5}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'mapping' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">{txt.mapping.title}</h2>
          <p className="text-gray-500 mb-4">{txt.mapping.subtitle}</p>
          
          {fieldMapping?.mappings && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {txt.mapping.notionField}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {txt.mapping.propbaseField}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {txt.mapping.type}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {txt.mapping.description}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {(fieldMapping.mappings as FieldMapping[]).map((mapping, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {mapping.notion_field}
                        {mapping.required && (
                          <span className="ml-1 text-red-500">*</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <code className="px-2 py-1 bg-gray-100 rounded text-xs">
                          {mapping.propbase_field}
                        </code>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                          {mapping.notion_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {mapping.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'preview' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold">{txt.preview.title}</h2>
                <p className="text-gray-500">{txt.preview.subtitle}</p>
              </div>
              <button
                onClick={handlePreview}
                disabled={isLoadingPreview}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoadingPreview ? txt.preview.loading : txt.preview.load}
              </button>
            </div>

            {preview && (
              <div className="space-y-4">
                <div className="text-sm text-gray-500">
                  {txt.preview.total}: <strong>{preview.total_projects}</strong>
                </div>

                {(preview.projects as PreviewProject[]).map((project: PreviewProject, i: number) => (
                  <div key={i} className="border rounded-lg p-4">
                    <h3 className="font-semibold text-lg mb-2">{project.name}</h3>
                    
                    {/* Parsed Data */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                      {Object.entries(project.parsed_data).map(([key, value]) => (
                        <div key={key} className="text-sm">
                          <span className="text-gray-500">{key}:</span>{' '}
                          <span className="font-medium">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Files */}
                    <div className="flex flex-wrap gap-4 text-sm">
                      {project.price_list_urls.length > 0 && (
                        <div>
                          <span className="text-gray-500">{txt.preview.priceFiles}:</span>{' '}
                          <span className="font-medium text-green-600">
                            {project.price_list_urls.length}
                          </span>
                        </div>
                      )}
                      {project.layout_urls.length > 0 && (
                        <div>
                          <span className="text-gray-500">{txt.preview.layouts}:</span>{' '}
                          <span className="font-medium">{project.layout_urls.length}</span>
                        </div>
                      )}
                      {project.gallery_urls.length > 0 && (
                        <div>
                          <span className="text-gray-500">{txt.preview.gallery}:</span>{' '}
                          <span className="font-medium">{project.gallery_urls.length}</span>
                        </div>
                      )}
                    </div>

                    {/* Errors */}
                    {project.errors.length > 0 && (
                      <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
                        {txt.preview.errors}: {project.errors.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'sync' && (
        <div className="space-y-6">
          {/* Sync Actions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">{txt.sync.title}</h2>
            <p className="text-gray-500 mb-6">{txt.sync.subtitle}</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => handleSync(true)}
                disabled={syncInProgress || !connectionStatus?.success}
                className="p-4 border-2 border-dashed rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                <i className="fas fa-vial text-2xl text-blue-600 mb-2"></i>
                <h3 className="font-semibold">{txt.sync.dryRun}</h3>
                <p className="text-sm text-gray-500">{txt.sync.dryRunDesc}</p>
              </button>

              <button
                onClick={() => handleSync(false)}
                disabled={syncInProgress || !connectionStatus?.success}
                className="p-4 border-2 border-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50"
              >
                <i className="fas fa-sync text-2xl text-blue-600 mb-2"></i>
                <h3 className="font-semibold">{txt.sync.fullSync}</h3>
                <p className="text-sm text-gray-500">{txt.sync.fullSyncDesc}</p>
              </button>
            </div>

            {syncInProgress && (
              <div className="mt-6 flex items-center justify-center space-x-2 text-blue-600">
                <i className="fas fa-spinner fa-spin"></i>
                <span>{txt.sync.inProgress}</span>
              </div>
            )}
          </div>

          {/* Sync Result */}
          {lastSyncResult && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">{txt.sync.result}</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-green-50 rounded">
                  <div className="text-2xl font-bold text-green-600">
                    {lastSyncResult.projects_created}
                  </div>
                  <div className="text-sm text-gray-500">{txt.sync.created}</div>
                </div>
                <div className="p-4 bg-blue-50 rounded">
                  <div className="text-2xl font-bold text-blue-600">
                    {lastSyncResult.projects_updated}
                  </div>
                  <div className="text-sm text-gray-500">{txt.sync.updated}</div>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-2xl font-bold text-gray-600">
                    {lastSyncResult.projects_skipped}
                  </div>
                  <div className="text-sm text-gray-500">{txt.sync.skipped}</div>
                </div>
                <div className="p-4 bg-red-50 rounded">
                  <div className="text-2xl font-bold text-red-600">
                    {lastSyncResult.projects_failed}
                  </div>
                  <div className="text-sm text-gray-500">{txt.sync.failed}</div>
                </div>
              </div>

              <div className="text-sm text-gray-500 mb-4">
                {txt.sync.syncedAt}: {new Date(lastSyncResult.synced_at).toLocaleString()}
              </div>

              {lastSyncResult.price_files_found.length > 0 && (
                <div className="mb-4 p-4 bg-yellow-50 rounded">
                  <h3 className="font-semibold text-yellow-800 mb-2">
                    {txt.sync.priceFilesFound}: {lastSyncResult.price_files_found.length}
                  </h3>
                  <ul className="text-sm text-yellow-700 space-y-1">
                    {lastSyncResult.price_files_found.map((f, i) => (
                      <li key={i}>
                        <strong>{f.project_name}</strong>: {f.price_urls.length} файлов
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {lastSyncResult.errors.length > 0 && (
                <div className="mb-4 p-4 bg-red-50 rounded">
                  <h3 className="font-semibold text-red-800 mb-2">{txt.sync.errors}</h3>
                  <ul className="text-sm text-red-600 space-y-1">
                    {lastSyncResult.errors.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {lastSyncResult.warnings.length > 0 && (
                <div className="p-4 bg-yellow-50 rounded">
                  <h3 className="font-semibold text-yellow-800 mb-2">{txt.sync.warnings}</h3>
                  <ul className="text-sm text-yellow-600 space-y-1">
                    {lastSyncResult.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Price Files */}
          {priceFiles && priceFiles.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-2">{txt.priceFiles.title}</h2>
              <p className="text-gray-500 mb-4">{txt.priceFiles.subtitle}</p>
              
              <div className="space-y-3">
                {priceFiles.map((pf: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <span className="font-medium">{pf.project_name}</span>
                      <span className="ml-2 text-sm text-gray-500">
                        {pf.price_urls.length} {txt.priceFiles.files}
                      </span>
                    </div>
                    <button
                      className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                      onClick={() => {
                        // Navigate to price ingestion page with pre-filled URL
                        // Or trigger direct parsing
                        console.log('Parse files:', pf.price_urls)
                      }}
                    >
                      {txt.priceFiles.parse}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
