import {mkdtemp, mkdir, readFile, rm, writeFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {afterEach, describe, expect, it} from 'vitest';
import {readAgentConfig, saveAgentConfig} from './config-store.mjs';

const roots = [];

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, {recursive: true, force: true})));
});

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), 'vimax-config-'));
  roots.push(root);
  await mkdir(path.join(root, 'configs'), {recursive: true});
  await writeFile(path.join(root, 'configs', 'agent.local.yaml'), [
    'llm:',
    '  model_provider: openai',
    '  model: existing-model',
    '  base_url: https://example.test/v1',
    '  api_key: secret-value',
    '',
  ].join('\n'));
  return root;
}

describe('agent config store', () => {
  it('never returns stored API keys', async () => {
    const root = await fixture();
    const config = await readAgentConfig(root);
    expect(config.sections.llm).toMatchObject({model: 'existing-model', api_key: '', has_api_key: true});
    expect(JSON.stringify(config)).not.toContain('secret-value');
  });

  it('keeps a stored key when a blank key is saved', async () => {
    const root = await fixture();
    await saveAgentConfig(root, {sections: {llm: {model: 'new-model', api_key: ''}}});
    const saved = await readFile(path.join(root, 'configs', 'agent.local.yaml'), 'utf8');
    expect(saved).toContain('model: new-model');
    expect(saved).toContain('api_key: secret-value');
  });

  it('rejects invalid base URLs', async () => {
    const root = await fixture();
    await expect(saveAgentConfig(root, {sections: {llm: {base_url: 'file:///tmp/key'}}})).rejects.toThrow(/http/);
  });

  it('allows empty or placeholder optional base_url fields (SenseNova empty video)', async () => {
    const root = await fixture();
    await saveAgentConfig(root, {
      sections: {
        video: {provider: '', model: '', base_url: ''},
        embedding: {model_provider: 'openai', model: '', base_url: '<YOUR_EMBEDDING_BASE_URL>'},
        reranker: {model: '', base_url: '<YOUR_RERANKER_BASE_URL>'},
      },
    });
    await saveAgentConfig(root, {
      sections: {
        video: {model: '<YOUR_VIDEO_MODEL>', base_url: '<YOUR_VIDEO_BASE_URL>'},
      },
    });
    const config = await readAgentConfig(root);
    expect(config.sections.video.base_url).toBe('<YOUR_VIDEO_BASE_URL>');
    expect(config.sections.embedding.base_url).toBe('<YOUR_EMBEDDING_BASE_URL>');
    expect(config.sections.reranker.base_url).toBe('<YOUR_RERANKER_BASE_URL>');
  });

  it('reads and saves video.provider for Settings ↔ agent.local.yaml', async () => {
    const root = await fixture();
    await saveAgentConfig(root, {sections: {video: {provider: 'google', model: 'veo-3', base_url: 'https://generativelanguage.googleapis.com'}}});
    const config = await readAgentConfig(root);
    expect(config.sections.video).toMatchObject({provider: 'google', model: 'veo-3'});
    const saved = await readFile(path.join(root, 'configs', 'agent.local.yaml'), 'utf8');
    expect(saved).toContain('provider: google');
  });

  it('rejects unsupported video providers', async () => {
    const root = await fixture();
    await expect(saveAgentConfig(root, {sections: {video: {provider: 'acme'}}})).rejects.toThrow(/openrouter|yunwu|google/);
  });

  it('round-trips embedding and reranker fields for novel2video Settings', async () => {
    const root = await fixture();
    await saveAgentConfig(root, {
      sections: {
        embedding: {
          model_provider: 'openai',
          model: 'text-embedding-3-small',
          base_url: 'https://api.openai.com/v1',
          api_key: 'embed-secret',
        },
        reranker: {
          model: 'BAAI/bge-reranker-v2-m3',
          base_url: 'https://api.siliconflow.cn/v1',
          api_key: 'rerank-secret',
        },
      },
    });
    const config = await readAgentConfig(root);
    expect(config.sections.embedding).toMatchObject({
      model_provider: 'openai',
      model: 'text-embedding-3-small',
      base_url: 'https://api.openai.com/v1',
      has_api_key: true,
      api_key: '',
    });
    expect(config.sections.reranker).toMatchObject({
      model: 'BAAI/bge-reranker-v2-m3',
      base_url: 'https://api.siliconflow.cn/v1',
      has_api_key: true,
      api_key: '',
    });
    expect(config.sections.reranker.model_provider).toBeUndefined();
  });
});
