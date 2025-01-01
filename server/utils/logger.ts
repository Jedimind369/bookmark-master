export const logger = {
    info: (message: string, meta?: object) => {
        console.log(`[INFO] ${message}`, meta ? meta : '');
    },
    error: (message: string, meta?: object) => {
        console.error(`[ERROR] ${message}`, meta ? meta : '');
    },
    debug: (message: string, meta?: object) => {
        if (process.env.NODE_ENV !== 'production') {
            console.debug(`[DEBUG] ${message}`, meta ? meta : '');
        }
    },
    warn: (message: string, meta?: object) => {
        console.warn(`[WARN] ${message}`, meta ? meta : '');
    }
}; 