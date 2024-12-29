import { jest } from '@jest/globals';

// Mock winston logger with simplified interface
jest.mock('winston', () => ({
    format: {
        combine: jest.fn(),
        timestamp: jest.fn(),
        json: jest.fn(),
        simple: jest.fn(() => jest.fn())
    },
    createLogger: jest.fn(() => ({
        error: jest.fn(),
        warn: jest.fn(),
        info: jest.fn(),
        add: jest.fn()
    })),
    transports: {
        File: jest.fn(),
        Console: jest.fn()
    }
}));

// Mock Bottleneck with reliable batch processing behavior
jest.mock('bottleneck', () => {
    return {
        __esModule: true,
        default: jest.fn().mockImplementation(() => ({
            schedule: jest.fn((fn) => Promise.resolve(fn())),
            on: jest.fn(),
            strategy: { BLOCK: 'BLOCK' }
        }))
    };
});

// Mock Response class focusing on essential functionality
class MockResponse implements Response {
    private _ok: boolean;
    private _status: number;
    private _body: any;
    private _headers: Map<string, string>;

    constructor(body: BodyInit | null = null, init: ResponseInit = {}) {
        this._status = init.status || 200;
        this._ok = this._status >= 200 && this._status < 300;
        this._body = body;
        this._headers = new Map(Object.entries(init.headers || {}));
    }

    get ok() { return this._ok; }
    get status() { return this._status; }
    get statusText() { return ''; }
    get type() { return 'basic' as ResponseType; }
    get url() { return ''; }
    get redirected() { return false; }
    
    async json() {
        return Promise.resolve(typeof this._body === 'string' ? JSON.parse(this._body) : this._body);
    }

    async text() {
        return Promise.resolve(typeof this._body === 'string' ? this._body : JSON.stringify(this._body));
    }

    get headers(): Headers {
        return new Headers(Object.fromEntries(this._headers.entries()));
    }

    // Implement required interface methods with minimal functionality
    clone(): Response { 
        return new MockResponse(this._body, { 
            status: this._status,
            headers: Object.fromEntries(this._headers.entries())
        }); 
    }
    
    get body() { return null; }
    get bodyUsed() { return false; }
    
    async arrayBuffer(): Promise<ArrayBuffer> { 
        return new ArrayBuffer(0); 
    }
    
    async blob(): Promise<Blob> { 
        return new Blob([]); 
    }
    
    async formData(): Promise<FormData> { 
        return new FormData(); 
    }
}

// Mock fetch with consistent behavior
const mockFetch = jest.fn(() => 
    Promise.resolve(new MockResponse(JSON.stringify({ 
        url: 'https://example.com',
        httpResponseBody: '<html></html>',
        httpResponseHeaders: {},
        statusCode: 200
    }), {
        status: 200,
        headers: { 'content-type': 'application/json' }
    }))
);

(global as any).fetch = mockFetch;
(global as any).Response = MockResponse;

export { mockFetch, MockResponse }; 