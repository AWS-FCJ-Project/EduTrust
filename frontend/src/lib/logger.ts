/**
 * Logging utility for CloudWatch integration
 * Logs are automatically sent to CloudWatch when running on Amplify
 */

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogContext {
  [key: string]: any;
}

class Logger {
  private isDevelopment = process.env.NODE_ENV === 'development';
  private isServer = typeof window === 'undefined';

  private formatMessage(level: LogLevel, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    
    if (context) {
      return `${prefix} ${message} ${JSON.stringify(context)}`;
    }
    
    return `${prefix} ${message}`;
  }

  info(message: string, context?: LogContext) {
    const formatted = this.formatMessage('info', message, context);
    console.log(formatted);
  }

  warn(message: string, context?: LogContext) {
    const formatted = this.formatMessage('warn', message, context);
    console.warn(formatted);
  }

  error(message: string, error?: Error | unknown, context?: LogContext) {
    const errorContext = {
      ...context,
      ...(error instanceof Error && {
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack,
        },
      }),
    };
    
    const formatted = this.formatMessage('error', message, errorContext);
    console.error(formatted);
  }

  debug(message: string, context?: LogContext) {
    if (this.isDevelopment) {
      const formatted = this.formatMessage('debug', message, context);
      console.debug(formatted);
    }
  }

  // API call logging
  apiCall(method: string, url: string, status?: number, duration?: number) {
    this.info('API Call', {
      method,
      url,
      status,
      duration,
      timestamp: Date.now(),
    });
  }

  // User action logging
  userAction(action: string, details?: LogContext) {
    this.info('User Action', {
      action,
      ...details,
      timestamp: Date.now(),
    });
  }

  // Performance logging
  performance(metric: string, value: number, unit: string = 'ms') {
    this.info('Performance Metric', {
      metric,
      value,
      unit,
      timestamp: Date.now(),
    });
  }
}

// Export singleton instance
export const logger = new Logger();

// Export for testing
export { Logger };
