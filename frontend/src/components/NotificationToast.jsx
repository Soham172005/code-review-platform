import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import useSSE from '../hooks/useSSE'
import { BellIcon } from '@heroicons/react/24/outline'

const EVENT_MESSAGES = {
  comment_added: 'New comment on your PR',
  review_submitted: 'A review was submitted',
  pr_state_changed: 'PR status changed',
  comment_resolved: 'A comment was resolved',
}

export default function NotificationToast() {
  const { user } = useAuth()
  const event = useSSE(user ? '/api/notifications/stream/' : null)

  useEffect(() => {
    if (event) {
      const message = event.message || EVENT_MESSAGES[event.event_type] || 'New notification'
      toast(message, {
        icon: <BellIcon className="h-5 w-5 text-indigo-500" />,
      })
    }
  }, [event])

  return null
}
