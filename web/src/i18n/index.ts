import {en, type MessageTree} from './en';
import {zhCN} from './zh-CN';

export type LocaleId = 'zh-CN' | 'en';

/** Default locale for the Web UI. Switch to `'en'` to restore English. */
export const DEFAULT_LOCALE: LocaleId = 'zh-CN';

const catalogs: Record<LocaleId, MessageTree> = {
  'zh-CN': zhCN,
  en,
};

let activeLocale: LocaleId = DEFAULT_LOCALE;

export function getLocale(): LocaleId {
  return activeLocale;
}

/** Runtime locale switch (tests / future language picker). */
export function setLocale(locale: LocaleId) {
  activeLocale = locale;
}

export function messages(): MessageTree {
  return catalogs[activeLocale];
}

type Params = Record<string, string | number>;

export function t(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => (
    params[key] === undefined || params[key] === null ? `{${key}}` : String(params[key])
  ));
}

export {en, zhCN};
