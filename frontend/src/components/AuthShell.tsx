import type { ReactNode } from 'react'
import { PHOTOS } from '../campusPhotos'

/** Log In / Create account layout: a Sterling Library photo panel next to the form card. */
export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="container section auth">
      <div className="auth-split reveal">
        <figure className="auth-photo" style={{ backgroundImage: `url("${PHOTOS.sterlingLibrary.src}")` }}>
          <figcaption>
            <strong>Your chat, saved.</strong>
            <span>Log in and we&apos;ll remember your sizes and favorites next time you stop by.</span>
          </figcaption>
        </figure>
        <div className="auth-card">{children}</div>
      </div>
    </div>
  )
}
