/** @type {import('jest').Config} */
const config = {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'node',
  roots: ['<rootDir>/server'],
  testMatch: ['**/*.test.ts'],
  moduleFileExtensions: ['ts', 'js', 'json', 'node'],
  setupFiles: ['<rootDir>/server/tests/setup.ts'],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov'],
  verbose: true,
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      useESM: true,
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
        lib: ['es2020', 'dom'],
        skipLibCheck: true,
        types: ['node', 'jest', '@types/node-fetch'],
        module: 'ESNext',
        moduleResolution: 'node'
      }
    }],
  },
  extensionsToTreatAsEsm: ['.ts'],
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(node-fetch|data-uri-to-buffer|fetch-blob|formdata-polyfill)/)'
  ],
  globals: {
    'ts-jest': {
      useESM: true,
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
        lib: ['es2020', 'dom'],
        skipLibCheck: true,
        types: ['node', 'jest', '@types/node-fetch'],
        module: 'ESNext',
        moduleResolution: 'node'
      }
    }
  }
};

export default config; 