import { customElement, property } from "lit/decorators.js";
import { css, html, LitElement, unsafeCSS, type CSSResultGroup, type HTMLTemplateResult, type PropertyValues } from "lit";
import { createRef, type Ref } from "lit/directives/ref.js";
import Prism from "prismjs";
import "prismjs/components/prism-typescript.js";
import "prismjs/components/prism-csv.js";
import "prismjs/components/prism-json.js";
import "prismjs/components/prism-bash.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import Theme from "prismjs/themes/prism-tomorrow.css?raw";

@customElement("bb-syntax-highlighting")
export class SyntaxHighlightingElement extends LitElement {
	public static styles?: CSSResultGroup = [
		unsafeCSS(Theme),
		css`
			:host {
				display: block;
				padding: 1rem;
				background: #262626;
				max-width: 100%;
				overflow-y: scroll;
			}
			syntax-highlight {
				tab-size: 8;
			}
		`
	];
	// Props
	@property({type: String})
	public language?: string;

	@property({type: String})
	public contents?: string;

	// Elements
	private highlightRef: Ref<HTMLElement>;

	public constructor() {
		super();
		this.highlightRef = createRef();
	}

	protected render(): HTMLTemplateResult {
		// @ts-ignore
		const grammar = Prism.languages[this.language];
		const highlighted = Prism.highlight(this.contents ?? "", grammar, this.language ?? "text");
		return html`
			<code class=${`language-${this.language}`}>${unsafeHTML(highlighted)}</code>
		`;
	}
	public updated(changedProperties: PropertyValues): void {
	    super.updated(changedProperties);

		const highlightElement = this.highlightRef.value;
		if (highlightElement === undefined) {
			return;
		}
		highlightElement.textContent = this.contents ?? "";
		(highlightElement as any).update();
	}

}
