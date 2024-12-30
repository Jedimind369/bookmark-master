import { jest } from '@jest/globals';

const mockFetch = jest.fn();
export default mockFetch;

export class Headers implements Iterable<[string, string]> {
  private headers: Map<string, string>;

  constructor(init?: Record<string, string> | Headers | string[][] | Map<string, string>) {
    this.headers = new Map();
    if (init) {
      if (init instanceof Map) {
        this.headers = new Map(init);
      } else if (Array.isArray(init)) {
        init.forEach(([key, value]) => this.headers.set(key, value));
      } else if (init instanceof Headers) {
        Array.from(init.entries()).forEach(([key, value]) => this.headers.set(key, value));
      } else {
        Object.entries(init).forEach(([key, value]) => this.headers.set(key, value));
      }
    }
  }

  append(name: string, value: string): void {
    this.headers.set(name, value);
  }

  delete(name: string): void {
    this.headers.delete(name);
  }

  get(name: string): string | null {
    return this.headers.get(name) || null;
  }

  has(name: string): boolean {
    return this.headers.has(name);
  }

  set(name: string, value: string): void {
    this.headers.set(name, value);
  }

  forEach(callbackfn: (value: string, key: string, parent: Headers) => void): void {
    this.headers.forEach((value, key) => callbackfn(value, key, this));
  }

  entries(): IterableIterator<[string, string]> {
    return this.headers.entries();
  }

  keys(): IterableIterator<string> {
    return this.headers.keys();
  }

  values(): IterableIterator<string> {
    return this.headers.values();
  }

  [Symbol.iterator](): IterableIterator<[string, string]> {
    return this.entries();
  }

  raw(): Record<string, string[]> {
    const raw: Record<string, string[]> = {};
    this.headers.forEach((value, key) => {
      raw[key.toLowerCase()] = [value];
    });
    return raw;
  }

  getSetCookie(): string[] {
    return [];
  }
}

export class Response {
  readonly ok: boolean;
  readonly status: number;
  readonly statusText: string;
  readonly headers: Headers;
  readonly body: null;
  private _bodyUsed: boolean;
  readonly url: string;
  readonly redirected: boolean;
  readonly type: ResponseType;
  private data: any;

  constructor(body?: any, init: { status?: number; statusText?: string; headers?: Record<string, string> | Record<string, string[]> } = {}) {
    this.data = body;
    this.status = init.status || 200;
    this.statusText = init.statusText || 'OK';
    this.ok = this.status >= 200 && this.status < 300;
    this.headers = new Headers(init.headers ? Object.entries(init.headers).reduce((acc, [key, value]) => {
      acc[key] = Array.isArray(value) ? value[0] : value;
      return acc;
    }, {} as Record<string, string>) : undefined);
    this.body = null;
    this._bodyUsed = false;
    this.url = 'https://example.com';
    this.redirected = false;
    this.type = 'default';
  }

  get bodyUsed(): boolean {
    return this._bodyUsed;
  }

  async json(): Promise<any> {
    if (this._bodyUsed) {
      throw new Error('Body has already been consumed');
    }
    this._bodyUsed = true;
    return this.data;
  }

  async text(): Promise<string> {
    if (this._bodyUsed) {
      throw new Error('Body has already been consumed');
    }
    this._bodyUsed = true;
    return typeof this.data === 'string' ? this.data : JSON.stringify(this.data);
  }

  async arrayBuffer(): Promise<ArrayBuffer> {
    if (this._bodyUsed) {
      throw new Error('Body has already been consumed');
    }
    this._bodyUsed = true;
    return new ArrayBuffer(0);
  }

  async blob(): Promise<Blob> {
    if (this._bodyUsed) {
      throw new Error('Body has already been consumed');
    }
    this._bodyUsed = true;
    return new Blob();
  }

  async formData(): Promise<FormData> {
    if (this._bodyUsed) {
      throw new Error('Body has already been consumed');
    }
    this._bodyUsed = true;
    return new FormData();
  }

  clone(): Response {
    return new Response(this.data, {
      status: this.status,
      statusText: this.statusText,
      headers: this.headers.raw()
    });
  }
} 