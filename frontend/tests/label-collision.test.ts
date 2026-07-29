import { describe, expect, it } from 'vitest'
import { rectanglesOverlap } from '../src/map/labelCollision'

describe('map label collision guard', () => {
  it('detects intersecting labels with the configured safety gap', () => {
    const first = { left: 0, right: 120, top: 0, bottom: 60 }
    const close = { left: 124, right: 244, top: 0, bottom: 60 }

    expect(rectanglesOverlap(first, close, 8)).toBe(true)
  })

  it('keeps labels that have enough separation at different resolutions', () => {
    const first = { left: 0, right: 120, top: 0, bottom: 60 }
    const separated = { left: 140, right: 260, top: 0, bottom: 60 }

    expect(rectanglesOverlap(first, separated, 8)).toBe(false)
  })
})
