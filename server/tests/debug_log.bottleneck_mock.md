# Debug Log: Bottleneck Mock Implementation
**Component**: ZyteService Tests  
**File**: `server/tests/setup.ts`  
**Issue Type**: Test Infrastructure  
**Created**: 2024-01-01  
**Status**: In Progress  

## Related Files
- `server/tests/zyte-service.test.ts`
- `server/services/zyteService.ts`

## Problem Description
Need to properly mock the Bottleneck rate limiter for testing the ZyteService. The mock needs to:
1. Support constructor instantiation
2. Provide a working schedule method
3. Handle promise resolution correctly
4. Include static strategy property

## Attempted Solutions

### 1. Simple Function Mock (❌ Failed)
```typescript
jest.fn().mockImplementation(() => ({ 
    schedule: jest.fn() 
}))
```
- **Error**: `Cannot read properties of undefined (reading 'ok')`
- **Root Cause**: Schedule function wasn't handling promises properly
- **Why Not Working**: Mock was too simplistic, didn't maintain promise chain

### 2. Mock Instance with Promise (❌ Failed)
```typescript
const mockBottleneckInstance = {
    schedule: jest.fn(() => Promise.resolve()),
    on: jest.fn()
};
```
- **Error**: `TypeError: bottleneck_1.default is not a constructor`
- **Root Cause**: Bottleneck needs to be a constructor function
- **Why Not Working**: Instance mock doesn't support `new` operator

### 3. Constructor Function (❌ Failed)
```typescript
function MockBottleneck(this: any) {
    Object.assign(this, mockBottleneckInstance);
    return this;
}
```
- **Error**: Property 'strategy' is not assignable to type 'Mock<UnknownFunction>'
- **Root Cause**: TypeScript type conflicts with Jest mock types
- **Why Not Working**: Type system conflicts between Jest and custom constructor

### 4. Class-Based Mock (❌ Failed)
```typescript
class MockBottleneck {
    schedule = jest.fn((fn: () => Promise<any>) => {
        try {
            return Promise.resolve(fn());
        } catch (error) {
            return Promise.reject(error);
        }
    });
    on = jest.fn();
    static strategy = { BLOCK: 'BLOCK' };
}

jest.mock('bottleneck', () => MockBottleneck);
```
- **Error**: `TypeError: bottleneck_1.default is not a constructor`
- **Root Cause**: Jest mock system doesn't properly handle class-based mocks for ES modules
- **Why Not Working**: The mock class isn't being properly recognized as a constructor by the ES module system

### 5. Factory Function with Jest Mock (🔄 In Progress)
```typescript
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
```
- **Status**: Encountering TypeScript error
- **Error**: `"fn" ist vom Typ "unbekannt"` (fn is of type unknown)
- **Root Cause**: TypeScript needs explicit type information for the schedule function parameter
- **Current Investigation**:
  1. The `fn` parameter in `schedule` needs proper typing
  2. Need to match Bottleneck's actual schedule method signature
  3. May need to import Bottleneck types for accurate typing
- **Potential Fix**:
```typescript
jest.mock('bottleneck', () => {
    return {
        __esModule: true,
        default: jest.fn().mockImplementation(() => ({
            schedule: jest.fn((fn: () => Promise<any>) => Promise.resolve(fn())),
            on: jest.fn(),
            strategy: { BLOCK: 'BLOCK' }
        }))
    };
});
```

## Next Steps
1. If current attempt fails after fixing types, try:
   - Using Jest's `requireActual` to extend real Bottleneck
   - Implementing a proxy-based mock
   - Creating a custom Jest transformer for ES module mocking

## Notes
- Mock needs to handle both successful and failed requests
- Must maintain proper promise chain for async operations
- TypeScript types must be properly maintained
- Need to ensure compatibility with Jest's mock system
- ES module mocking requires special handling in Jest
- Proper typing is crucial for maintainability and catching errors early 