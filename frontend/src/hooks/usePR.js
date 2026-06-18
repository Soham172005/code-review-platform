import { useQuery } from '@tanstack/react-query'
import { getPR } from '../api'

export default function usePR(id) {
  return useQuery({
    queryKey: ['pr', id],
    queryFn: () => getPR(id).then((res) => res.data),
    enabled: !!id,
  })
}
