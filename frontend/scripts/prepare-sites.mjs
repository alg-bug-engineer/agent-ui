import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const serverDirectory = resolve('dist/server')
const workerEntry = `export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request)
    if (
      response.status === 404
      && request.method === 'GET'
      && (request.headers.get('accept') || '').includes('text/html')
    ) {
      const fallbackUrl = new URL(request.url)
      fallbackUrl.pathname = '/index.html'
      return env.ASSETS.fetch(new Request(fallbackUrl, request))
    }
    return response
  },
}
`

await mkdir(serverDirectory, { recursive: true })
await writeFile(resolve(serverDirectory, 'index.js'), workerEntry, 'utf8')
