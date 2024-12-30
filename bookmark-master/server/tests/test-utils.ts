import { Response, Headers } from './__mocks__/node-fetch.js';
import { ZyteResponse } from '../services/zyteService.js';

export function createMockResponse(data: ZyteResponse | any, headers: Map<string, string> = new Map()): Response {
  const headerObj: Record<string, string[]> = {};
  headers.forEach((value, key) => {
    headerObj[key.toLowerCase()] = [value];
  });

  return new Response(data, {
    status: 200,
    statusText: 'OK',
    headers: headerObj
  });
} 