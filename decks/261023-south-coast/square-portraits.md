# Square contributor portraits

The featured Dan Barber portrait on visible slide 2 and Ian Tweedie portrait on
visible slide 4 use the same 236px square frame and 20px corner radius as Areti
Iles on slide 3. Small roster portraits retain their original source images.
The converter preserves these featured portrait selections.

- Dan: `public/slides/261023-south-coast/dan-barber-square.png`.
  The built-in imagegen tool extended the original circular photo's white
  corners into a square photo. Original `image33.jpeg` is retained.
- Ian: `public/slides/261023-south-coast/ian-tweedie-square.jpeg`.
  Copied byte-for-byte from the original rectangular photograph already at
  `public/slides/260925-little-code/brand/ian-tweedie.jpeg`. Original
  `image42.jpeg` is retained.

## Dan image edit prompt

Use case: identity-preserve. Asset type: square speaker portrait for a presentation. Input image 1 is the edit target: Dan Barber's photo has been cropped into a circle with plain white corners. Convert this existing photo into a full square photograph ONLY by filling the blank white corners outside the circular photograph with natural continuations of the existing light gray wall in the upper corners and black shirt/shoulders in the lower corners. Preserve the original photograph inside the circle as exactly as possible: same person, exact face, expression, hair, beard, skin texture, pose, shirt, lighting, framing and scale. Do not retouch, beautify, change facial features or reposition the face. Keep the full original head visible at the same scale. Final image: one square photo, no circular edge, no white corners, no border, no rounded frame, no added objects, no text or watermark. Save the generated image and return its filesystem path so it can be copied into the repository.
