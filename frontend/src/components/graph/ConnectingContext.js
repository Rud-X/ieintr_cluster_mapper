import { createContext } from 'react'

/**
 * Context that carries the currently-dragged connection state.
 * When a user drags from a port:
 *   { sourceStreamId, sourceCompanyId, sourceDirection }
 * When no drag is in progress: null
 */
export const ConnectingContext = createContext(null)
