import { HttpError, ApiService } from "@/services/api";

export const handleOAuthRequestsIn = async <T>(fn: () => Promise<T>, api: ApiService): Promise<T> => {
  while (true) {
    try {
      return await fn()
    } catch (e) {
      const oauthRequest = parseOAuthRequest(e);
      if (oauthRequest) {
        await oauthPopupFlow(oauthRequest, api);
      } else {
        throw e;
      }
    }
  }
}

const parseOAuthRequest = (e: unknown): { url: string, state: string } | undefined => {
  if (!(e instanceof HttpError && e.status === 401 && e.body)) {
    return undefined
  }
  try {
    const body = JSON.parse(e.body);
    if (!body.detail) {
      return undefined
    }
    return new OAuthRequest(body.detail?.oauthUrl, body.detail?.oauthState);
  } catch (_) {
    return undefined
  }
}

class OAuthRequest {
  url: string
  state: string

  constructor(url: string, state: string) {
    this.url = url;
    this.state = state;
  }
}

export class AuthenticationError extends Error {
  errorCode: string

  constructor(errorCode: string) {
    super('Authentication error: ' + errorCode);
    this.errorCode = errorCode;
  }
}

const oauthPopupFlow = async (oauthRequest: OAuthRequest, api: ApiService): Promise<void> => {
  return new Promise((resolve, reject) => {
    const popupWidth = 600;
    const popupHeight = 600;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;
    const popup = window.open(oauthRequest.url, 'oauth', `popup,width=${popupWidth},height=${popupHeight},left=${left},top=${top}`);
    if (!popup) {
      reject(new Error('Failed to open popup'));
      return;
    }

    // using broadcast channel instead of just using popup and window opener since some mcp servers (like sentry)
    // can set Cross Origin Opener Policy (COOP) which prevents the popup from accessing the opener window
    const channel = new BroadcastChannel('oauth_channel');
    const cleanup = () => {
      channel.close();
      channel.removeEventListener('message', handleCallback);
    };

    const handleCallback = async (event: MessageEvent) => {
      const data = event.data;
      if (data.type === 'oauth_callback' && data.state === oauthRequest.state) {
        try {
          cleanup();
          if (data.error) {
            await api.deleteToolAuth(data.toolId, data.state);
            reject(new AuthenticationError(data.error == 'access_denied' ? 'authenticationAccessDenied' : 'authenticationUnknownError'));
          } else {
            await api.completeToolAuth(data.toolId, data.state, data.code);
            resolve()
          }
        } catch (error) {
          if (error instanceof HttpError && error.status === 400) {
            try {
              const body = JSON.parse(error.body);
              if (body.detail && body.detail === "Authentication cancelled") {
                reject(new AuthenticationError('authenticationCancelled'));
                return
              }
            } catch (_) {
            }
          }
          reject(error);
        }
      }
    };

    channel.addEventListener('message', handleCallback);
  });
}
