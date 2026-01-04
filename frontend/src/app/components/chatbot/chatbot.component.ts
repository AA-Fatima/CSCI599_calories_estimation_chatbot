import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService } from '../../services/chat.service';
import { Message } from '../../models/chat.model';

@Component({
  selector: 'app-chatbot',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chatbot.component.html',
  styleUrl: './chatbot.component.scss'
})
export class ChatbotComponent implements OnInit {
  messages: Message[] = [];
  userInput = '';
  country = '';
  sessionId = '';
  loading = false;

  quickQueries = [
    'Shawarma calories',
    'Falafel',
    'Kushari',
    'fajita',
    'Kabsa'
  ];
  constructor(
    private chatService: ChatService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.country = params['country'] || '';
      if (!this.country) {
        this.router.navigate(['/']);
      }
    });

    
    // Add welcome message
    const botMessage: Message = {
          type: 'bot',
          content: this.getWelcomeMessage(),
          timestamp: new Date()
        };
        this.messages.push(botMessage);
  }

  getWelcomeMessage(): string {
    const countryName = this.country || 'your country';
    return `🍽️ Welcome!  I'm your Arabic Food Calorie Calculator for ${this.country || ''} Ask me about any dish or ingredient, and I'll tell you the calories!\n\nExamples:\n• "How many calories in shawarma? "\n• "Falafel without tahini"\n• "200g grilled chicken"`;
  }

  sendMessage() {
    if (!this.userInput.trim() || this.loading) return;

    const userMessage: Message = {
      type: 'user',
      content: this.userInput,
      timestamp: new Date()
    };
    this.messages.push(userMessage);

    const messageContent = this.userInput;
    this.userInput = '';
    this.loading = true;

    this.chatService.sendMessage({
      message: messageContent,
      session_id: this.sessionId || undefined,
      country: this.country
    }).subscribe({
      next: (response) => {
        this.sessionId = response.session_id;
        const botMessage: Message = {
          type: 'bot',
          content: response.message,
          response: response,
          timestamp: new Date()
        };
        this.messages.push(botMessage);
        this.loading = false;
      },
      error: (error) => {
        console.error('Error:', error);
        const errorMessage: Message = {
          type: 'bot',
          content: 'Sorry, there was an error processing your request.',
          timestamp: new Date()
        };
        this.messages.push(errorMessage);
        this.loading = false;
      }
    });
  }

  sendQuickQuery(query: string): void {
    this.userInput = query;
    this.sendMessage();
  }

  handleKeyPress(event:  KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
   goHome() {
    this.router.navigate(['/']);
  }
}
