import { css, html, LitElement, type CSSResultGroup, type HTMLTemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

const FLASK_WAVE_LENGTH = 10;

@customElement("bb-curse-wave-visualization")
export class WaveVisualizationElement extends LitElement {
	// Props
	@property({type: Number})
	public resolution: number;

	@property({type: Number})
	public offset: number;

	@property({type: Number})
	public variation: number;

	@property({type: Array})
	public controls?: string[];

	// Attrs
	private canvasContext: CanvasRenderingContext2D;

	public constructor() {
		super();
		this.resolution = 20;
		this.offset = 0;
		this.variation = 0;

		const canvas = document.createElement("canvas");
		this.canvasContext = canvas.getContext("2d");
	}
	protected render() {
		const height = this.canvasContext.canvas.height;
		const width = this.canvasContext.canvas.width;
		
		this.canvasContext.reset();
		
		const waveSize = 0.5;
		const topOffset = 0.25;
		
		// Render the sine wave as a base
		for (let x = 0; x < width; x++) {
			const y = Math.sin(x / width * Math.PI * 2 + this.offset);
			const yAtScale = ((y + 1) / 2 * waveSize + topOffset) * height;
			this.canvasContext.fillRect(x, yAtScale, 1, 1);
		}

		const angleIncrement = (Math.PI * 2) / this.resolution;
		const points: number[] = [];
		for (let pointIndex = 0; pointIndex <= this.resolution; pointIndex++) {
			let point = Math.sin((angleIncrement * pointIndex) + this.offset) * FLASK_WAVE_LENGTH;
			points.push(point);
		}
		
		this.canvasContext.beginPath();
		for (const [index, point] of points.entries()) {
			const xAtScale = index * (width / this.resolution);
			const variationMultiplier = 1 - (this.variation / 2) + (Math.random() * this.variation);
			const y = Math.sin((angleIncrement * index) + this.offset) * variationMultiplier;
			const yAtScale = ((y + 1) / 2 * waveSize + topOffset) * height;
			
			if (index === 0) {
				this.canvasContext.moveTo(xAtScale, yAtScale);
			} else {
				this.canvasContext.lineTo(xAtScale, yAtScale);
			}
		}
		this.canvasContext.strokeStyle = "blue";
		this.canvasContext.stroke();
		
		for (const [index, point] of points.entries()) {
			const xAtScale = index * (width / this.resolution);
			const variationMultiplier = 1 - (this.variation / 2) + (Math.random() * this.variation);
			const y = Math.sin((angleIncrement * index) + this.offset) * variationMultiplier;
			const yAtScale = ((y + 1) / 2 * waveSize + topOffset) * height;
			
			const radius = 5;
			this.canvasContext.beginPath();
			this.canvasContext.arc(xAtScale, yAtScale, radius, 0, Math.PI * 2);
			this.canvasContext.strokeStyle = "red";
			this.canvasContext.stroke();
		}

		return html`
			${this.canvasContext.canvas}
			<div id="controls">
				<div class="control" ?hidden=${this.controls !== undefined && !this.controls.includes("offset")}>
					<label for="input-offset">Offset</label>
					<input
						id="input-offset"
						type="range"
						min="0"
						max="1"
						step="0.01"
						.value=${this.offset} @input=${(event) => {
							const input = event.target as HTMLInputElement;
							this.offset = parseFloat(input.value);
						}}
					>
				</div>
				<div class="control" ?hidden=${this.controls !== undefined && !this.controls.includes("resolution")}>
					<label for="input-resolution">Resolution</label>
					<input
						id="input-resolution"
						type="range"
						min="0"
						max="100"
						.value=${this.resolution}
						@input=${(event) => {
							const input = event.target as HTMLInputElement;
							this.resolution = parseInt(input.value);
						}}
					>
				</div>
				<div class="control" ?hidden=${this.controls !== undefined && !this.controls.includes("variation")}>
					<label for="input-variation">Variation</label>
					<input
						id="input-variation"
						type="range"
						min="0"
						step="0.01"
						max="1"
						.value=${this.variation}
						@input=${(event) => {
							const input = event.target as HTMLInputElement;
							this.variation = parseFloat(input.value);
						}}
					>
				</div>
			</div>
		`;
	}
}
