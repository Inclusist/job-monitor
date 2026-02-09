import { useQuery } from '@tanstack/react-query';
import { getMatchingStatus } from '../services/jobs';
import type { MatchingStatus } from '../types';

const IDLE_STATUS: MatchingStatus = {
  status: 'idle',
  progress: 0,
  message: 'Not running',
};

export function useMatchingStatus(enabled: boolean) {
  return useQuery({
    queryKey: ['matching-status'],
    queryFn: getMatchingStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'running') return 1000;
      return false;
    },
    enabled,
    initialData: IDLE_STATUS,
  });
}
