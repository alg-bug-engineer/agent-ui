export interface RectangleBounds {
  left: number
  right: number
  top: number
  bottom: number
}

export function rectanglesOverlap(
  left: RectangleBounds,
  right: RectangleBounds,
  padding = 8,
) {
  return !(
    left.right + padding <= right.left
    || right.right + padding <= left.left
    || left.bottom + padding <= right.top
    || right.bottom + padding <= left.top
  )
}
