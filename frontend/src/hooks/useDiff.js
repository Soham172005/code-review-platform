import { useQuery } from '@tanstack/react-query'
import { getDiff } from '../api'

export default function useDiff(prId) {
  return useQuery({
    queryKey: ['diff', prId],
    queryFn: () => getDiff(prId).then((res) => res.data),
    enabled: !!prId,
  })
}
