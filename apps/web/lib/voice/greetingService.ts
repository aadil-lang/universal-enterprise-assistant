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
  public generateGreeting(user?: ArchieUserProfile | null, now: Date = new Date()): string {
    const hours = now.getHours();
    let timeGreeting = 'Good afternoon';
    if (hours < 12) {
      timeGreeting = 'Good morning';
    } else if (hours >= 17) {
      timeGreeting = 'Good evening';
    }

    const name = this.resolveEmployeeName(user);

    if (name) {
      // Examples:
      // Morning: "Hey Aadil! Good morning. Welcome back. How can I help you today?"
      // Afternoon: "Hey Bob! Good afternoon. What can I help you with?"
      // Evening: "Hey Alice! Good evening. How can I help you today?"
      if (hours < 12) {
        return `Hey ${name}! ${timeGreeting}. Welcome back. How can I help you today?`;
      } else if (hours < 17) {
        return `Hey ${name}! ${timeGreeting}. What can I help you with?`;
      } else {
        return `Hey ${name}! ${timeGreeting}. How can I help you today?`;
      }
    }

    // Neutral fallback
    return `Hello! ${timeGreeting}. Welcome to Acme Assistant. How can I help you today?`;
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
