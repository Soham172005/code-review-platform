import { useQuery } from '@tanstack/react-query'
import { getPR } from '../api'

export default function useComments(prId) {
  return useQuery({
    queryKey: ['comments', prId],
    queryFn: async () => {
      const res = await getPR(prId)
      const reviews = res.data.reviews || []
      return reviews.flatMap((r) =>
        (r.comments || []).map((c) => ({ ...c, reviewer: r.reviewer }))
      )
    },
    enabled: !!prId,
  })
}
