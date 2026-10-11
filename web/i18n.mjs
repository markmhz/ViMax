/** Server-side UI/API messages. Default zh-CN; set LOCALE to 'en' to restore English. */

export const LOCALE = 'zh-CN';

const en = {
  projectNotFound: 'Project not found',
  projectNameTooLong: 'Project name must be 64 characters or fewer',
  messageRequired: 'Message text is required',
  agentNotRunning: 'Agent is not running',
  notFound: 'Not found',
  chooseSession: 'Choose either a new or existing session',
  creatingWorkspace: 'Creating workspace',
  openingWorkspace: 'Opening workspace',
  agentReady: 'Agent ready',
  agentConnected: 'Agent connected',
  agentIdle: 'Agent idle',
  switchingWorkspace: 'Switching workspace',
  configurationUpdated: 'Configuration updated',
  generationStopped: 'Generation stopped',
  bodyTooLarge: 'Request body is too large',
  artifactNotFound: 'Artifact not found',
  configSectionsRequired: 'Configuration sections are required',
  sessionNotDirectory: 'Session workspace is not a directory',
  uploadDirUnsafe: 'Workspace upload directory is not safe',
  uniqueUploadFailed: 'Could not allocate a unique upload filename',
  completed: 'Completed',
  toolFailed: 'Tool failed',
  artifactPathEscape: 'Artifact path escapes the active session',
  sessionPathEscape: 'Session path escapes .working_dir',
  invalidSessionId: 'Invalid session id',
  validFilenameRequired: 'A valid filename is required',
  filenameTooLong: 'Filename must be 180 characters or fewer',
  filenameUnsupported: 'Filename contains unsupported characters',
  uploadLimit: 'File exceeds the {limit} upload limit',
  agentProcessError: 'Agent process error: {detail}',
  agentStoppedBy: 'Agent stopped by {signal}',
  agentExited: 'Agent exited with code {code}',
  configMustBeMapping: 'configs/agent.local.yaml must be a YAML mapping',
  mustBeString: '{label} must be a string',
  tooLong: '{label} is too long',
  mustUseHttp: '{label} must use http:// or https://',
  invalidVideoProvider: '{label} must be openrouter, yunwu, google, or empty',
};

const zhCN = {
  projectNotFound: '未找到项目',
  projectNameTooLong: '项目名称不能超过 64 个字符',
  messageRequired: '消息内容不能为空',
  agentNotRunning: '智能体未运行',
  notFound: '未找到',
  chooseSession: '请选择新建会话或已有会话之一',
  creatingWorkspace: '正在创建工作区',
  openingWorkspace: '正在打开工作区',
  agentReady: '智能体已就绪',
  agentConnected: '智能体已连接',
  agentIdle: '智能体空闲',
  switchingWorkspace: '正在切换工作区',
  configurationUpdated: '配置已更新',
  generationStopped: '生成已停止',
  bodyTooLarge: '请求体过大',
  artifactNotFound: '未找到产物',
  configSectionsRequired: '需要提供配置分区',
  sessionNotDirectory: '会话工作区不是目录',
  uploadDirUnsafe: '工作区上传目录不安全',
  uniqueUploadFailed: '无法分配唯一的上传文件名',
  completed: '已完成',
  toolFailed: '工具失败',
  artifactPathEscape: '产物路径超出当前会话范围',
  sessionPathEscape: '会话路径超出 .working_dir',
  invalidSessionId: '无效的会话 ID',
  validFilenameRequired: '需要有效的文件名',
  filenameTooLong: '文件名不能超过 180 个字符',
  filenameUnsupported: '文件名包含不支持的字符',
  uploadLimit: '文件超过 {limit} 上传限制',
  agentProcessError: '智能体进程错误：{detail}',
  agentStoppedBy: '智能体被 {signal} 停止',
  agentExited: '智能体已退出，代码 {code}',
  configMustBeMapping: 'configs/agent.local.yaml 必须是 YAML 映射',
  mustBeString: '{label} 必须是字符串',
  tooLong: '{label} 过长',
  mustUseHttp: '{label} 必须使用 http:// 或 https://',
  invalidVideoProvider: '{label} 必须是 openrouter、yunwu、google 或留空',
};

const catalogs = {en, 'zh-CN': zhCN};

export function msg(key, params) {
  let text = catalogs[LOCALE]?.[key] ?? catalogs.en[key] ?? key;
  if (params) {
    text = text.replace(/\{(\w+)\}/g, (_, name) => (
      params[name] === undefined || params[name] === null ? `{${name}}` : String(params[name])
    ));
  }
  return text;
}
