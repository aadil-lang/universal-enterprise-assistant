/**
 * Archie Personalized Greeting Service (ESR-STD-v2.4 §5).
 * 
 * Rules:
 * - Greet the currently authenticated employee using preferred name.
 * - Fallback order: preferred_name -> first_name -> display name -> neutral greeting.
 * - Local time greeting: Morning (< 12), Afternoon (12 to 17), Evening (>= 17).
 * - Greet once when a voice session begins; do not repeat greeting after every utterance.
 * - Never trust a user-spoken name as identity proof.
 */

import type { ArchieUserProfile } from './types.ts';

export class GreetingService {
  private hasGreetedSession: boolean = false;

  /**
   * Generates time-of-day appropriate greeting for the authenticated employee.
   */
  public generateGreeting(user?: ArchieUserProfile | null, now: Date = new Date(), userSpokenUtterance?: string): string {
    const hours = now.getHours();
    let timeGreeting = 'Good afternoon';
    if (hours < 12) {
      timeGreeting = 'Good morning';
    } else if (hours >= 17) {
      timeGreeting = 'Good evening';
    }

    const name = this.resolveEmployeeName(user);

    let salutation = 'Hey';
    if (userSpokenUtterance) {
      const q = userSpokenUtterance.toLowerCase().trim();
      if (q.startsWith('hi')) salutation = 'Hi';
      else if (q.startsWith('hey')) salutation = 'Hey';
      else if (q.startsWith('hello')) salutation = 'Hello';
      else if (q.includes('good morning')) salutation = 'Good morning';
      else if (q.includes('good afternoon')) salutation = 'Good afternoon';
      else if (q.includes('good evening')) salutation = 'Good evening';
      else if (q.startsWith('howdy')) salutation = 'Howdy';
    }

    if (name) {
      if (salutation === 'Hey') {
        return `Hey ${name}! ${timeGreeting}. I'm Archie, your HR and IT assistant. How can I help you today?`;
      }
      return `${salutation}, ${name}! I'm Archie, your HR and IT assistant. How can I help you today?`;
    }

    // Neutral fallback
    return `Hello! ${timeGreeting}. I'm Archie, your Acme HR and IT assistant. How can I help you today?`;
  }

  public shouldGreet(): boolean {
    return !this.hasGreetedSession;
  }

  public markGreeted(): void {
    this.hasGreetedSession = true;
  }

  public resetSession(): void {
    this.hasGreetedSession = false;
  }

  private resolveEmployeeName(user?: ArchieUserProfile | null): string | null {
    if (!user) return null;

    if (user.preferred_name && user.preferred_name.trim().length > 0) {
      return user.preferred_name.trim();
    }

    if (user.first_name && user.first_name.trim().length > 0) {
      return user.first_name.trim();
    }

    if (user.last_name && user.last_name.trim().length > 0) {
      return user.last_name.trim();
    }

    return null;
  }
}
