import { UserManager, Log, User, WebStorageStateStore } from 'oidc-client-ts'
import { Manifest, findManifest } from '@/services/api'


const config: Manifest = await findManifest()

class AuthService {
  private userManager: UserManager

  constructor() {
    const baseUrl = window.location.origin
    Log.setLogger(console)
    Log.setLevel(import.meta.env.DEV ? Log.DEBUG : Log.WARN)

    this.userManager = new UserManager({
      authority: config.auth.url,
      redirect_uri: `${baseUrl}/callback`,
      client_id: config.auth.clientId,
      scope: config.auth.scope,
      post_logout_redirect_uri: `${baseUrl}/landing`,
      silent_redirect_uri: `${baseUrl}/silent-renew`,
      userStore: new WebStorageStateStore({ store: window.localStorage })
    })

    this.userManager.events.addAccessTokenExpiring(async () => {
      console.debug('Access token expiring, attempting silent renew...')
      await this.renewToken()
    })

    this.userManager.events.addAccessTokenExpired(async () => {
      console.debug('Access token expired')
      await this.renewToken()
    })

    this.userManager.events.addSilentRenewError((error) => console.error('Silent Renew Error：', error))

    this.userManager.events.addUserSignedOut(async () => {
      console.debug('User signed out from another tab/window')
      await this.userManager.signoutRedirect()
    })
  }

  async login() {
    await this.userManager.signinRedirect()
  }

  async loginCallback() {
    try {
      await this.userManager.signinRedirectCallback()
    } catch (error) {
      console.debug('Login callback failed, attempting token renewal:', error)
      return await this.renewToken()
    }
  }

  async getUser(): Promise<User | null> {
    const user = await this.userManager.getUser()
    if (user && !user.expired) {
      return user
    }

    try {
      return await this.userManager.signinSilent()
    } catch (err) {
      return null
    }
  }

  async renewToken(): Promise<void> {
    try {
      await this.userManager.signinSilent()
    } catch (err) {
      await this.login()
    }
  }

  async renewCallback() {
    await this.userManager.signinSilentCallback()
  }

  async logout() {
    await this.userManager.signoutRedirect()
  }
}

const auth = new AuthService()

export default auth
export { config }
