import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '../store/authStore'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().optional(),
})

type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser, isLoading } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterForm) => {
    setError(null)
    try {
      await registerUser(data)
      toast.success('Account created successfully!')
      navigate('/')
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed'
      setError(message)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="first_name" className="label">
            First name
          </label>
          <input
            {...register('first_name')}
            type="text"
            className={errors.first_name ? 'input-error' : 'input'}
          />
          {errors.first_name && (
            <p className="mt-1 text-sm text-red-600">{errors.first_name.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="last_name" className="label">
            Last name
          </label>
          <input
            {...register('last_name')}
            type="text"
            className={errors.last_name ? 'input-error' : 'input'}
          />
        </div>
      </div>

      <div>
        <label htmlFor="email" className="label">
          Email address
        </label>
        <input
          {...register('email')}
          type="email"
          autoComplete="email"
          className={errors.email ? 'input-error' : 'input'}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="label">
          Password
        </label>
        <input
          {...register('password')}
          type="password"
          autoComplete="new-password"
          className={errors.password ? 'input-error' : 'input'}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
        )}
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="btn-primary w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Creating account...
          </>
        ) : (
          'Create account'
        )}
      </button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          Sign in
        </Link>
      </p>
    </form>
  )
}
